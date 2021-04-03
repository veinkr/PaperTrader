# -*- coding:utf-8 -*-
"""
模拟账户类
filename : paper_account.py
createtime : 2021/4/2 20:44
author : Demon Finch
"""
import uuid
import pandas as pd
from datetime import datetime, timedelta

order_history_temple = pd.DataFrame(columns=["order_id", "order_type", "price", "volume", "is_frozen",
                                             "commission", "tax", "datetime"])


class ORDER_DIRECTION:
    """订单的买卖方向
    BUY 股票 买入
    SELL 股票 卖出
    BUY_OPEN 期货 多开
    BUY_CLOSE 期货 空平(多头平旧仓)
    SELL_OPEN 期货 空开
    SELL_CLOSE 期货 多平(空头平旧仓)
    ASK  申购
    """

    BUY = 1
    SELL = -1
    BUY_OPEN = 2
    BUY_CLOSE = 3
    SELL_OPEN = -2
    SELL_CLOSE = -3
    SELL_CLOSETODAY = -4
    BUY_CLOSETODAY = 4
    ASK = 0
    XDXR = 5
    OTHER = 6


class ORDER_STATUS:
    """订单的买卖方向
    WAIT 委托中，尚未成交
    DONE 已成交
    CANCEL 取消订单
    """
    WAIT = 0
    DONE = 1
    CANCEL = 2


class MARKET:
    """
    市场
    stock_cn A股股票
    index_cn A股指数
    etf_cn A股ETF
    """
    stock_cn = "stock_cn"
    index_cn = "index_cn"
    etf_cn = "etf_cn"


class Paperorder:
    def __init__(self,
                 code: str,
                 order_time: datetime,
                 order_price: float,
                 order_volume: int,
                 order_type: int,
                 commisson: float = 0.0001,
                 tax_percent: float = 0.001,
                 order_id=str(uuid.uuid1())):
        self.code = code
        self.order_time = order_time
        self.order_price = order_price
        self.order_volume = order_volume

        self.deal_time = None
        self.deal_price = None
        self.deal_volume = None

        self.order_type = order_type
        self.commisson = commisson
        self.tax_percent = tax_percent
        self.order_id = order_id
        self.order_status = ORDER_STATUS.WAIT

    def __repr__(self):
        return str({"code": self.code,
                    "order_time": self.order_time,
                    "order_price": self.order_price,
                    "order_volume": self.order_volume,
                    "deal_time": self.deal_time,
                    "deal_price": self.deal_price,
                    "deal_volume": self.deal_volume,
                    "deal_money": self.deal_money,
                    "order_type": self.order_type,
                    "commisson": self.deal_commisson,
                    "tax_percent": self.deal_tax,
                    "order_id": self.order_id,
                    "order_status": self.order_status, })

    @property
    def frozen_money(self):
        return self.order_price * self.order_volume * (1 + self.commisson)

    @property
    def sell_money(self):
        if self.order_type == ORDER_DIRECTION.SELL:
            return self.deal_price * self.order_volume * (1 - self.commisson - self.tax_percent)
        else:
            return None

    @property
    def deal_money(self):
        if self.deal_price:
            return self.deal_price * self.order_volume * (1 + self.commisson)
        else:
            return None

    @property
    def deal_commisson(self):
        if self.deal_price:
            return self.deal_price * self.order_volume * self.commisson
        else:
            return None

    @property
    def deal_tax(self):
        if self.order_type == ORDER_DIRECTION.SELL:
            return self.deal_price * self.order_volume * self.tax_percent
        else:
            return 0

    @property
    def order_position(self) -> dict:
        """转化order为持仓类需要的数据"""
        positon_dict = {
            "order_id": self.order_id,
            "order_type": self.order_type,
            "price": self.deal_price,
            "volume": self.deal_volume if self.order_type in [ORDER_DIRECTION.BUY] else self.deal_volume * (-1),
            "commission": self.deal_commisson,
            "tax": self.deal_tax,
            "is_frozen": 1 if self.order_type in [ORDER_DIRECTION.BUY] else 0,
            "cbj_money": self.deal_money if self.order_type in [ORDER_DIRECTION.BUY] else self.sell_money * (-1),
            "datetime": self.deal_time}
        return positon_dict


class Paperpositon:

    def __init__(self,
                 code: str,
                 t: int,  # t+1
                 code_type: str,
                 ):
        self.code = code
        self.code_type = code_type  # 预留，处理期货时算法与A股不一致
        self.t = t
        self.cost_money = 0
        self.gpye = 0
        self.djsl = 0
        self.current_price = None
        self.order_history = order_history_temple  # tips：卖出时候，volume为负数
        self.old_history = list()

    def __repr__(self):
        return str({"code": self.code,
                    "code_type": self.code_type,
                    "cost_money": self.cost_money,
                    "gpye": self.gpye,
                    "djsl": self.djsl,
                    "kyye": self.kyye,
                    "order_history": self.order_history.to_dict(orient="records"),
                    })

    def settle(self):
        return {"code": self.code,
                "code_type": self.code_type,
                "cost_money": self.cost_money,
                "gpye": self.gpye,
                "djsl": self.djsl,
                "kyye": self.kyye,
                }

    @property
    def kyye(self):
        return self.gpye - self.djsl

    def add_order(self, order_info: Paperorder, current_time: datetime):
        self.order_history = self.order_history.append(order_info.order_position, ignore_index=True)
        self.cpt_djsl(current_time)
        self.gpye += order_info.order_position['volume']
        if self.code_type == "stock_cn":
            if self.gpye > 0 and self.order_history.shape[0] > 0:
                self.cost_money = self.cost_money + order_info.deal_money
            elif self.gpye == 0 and self.order_history.shape[0] > 0:
                self.old_history.append(self.order_history)
                self.order_history = order_history_temple
                self.cost_money = 0
        self.cpt_djsl(current_time)

    def cpt_djsl(self, current_time):
        """计算冻结股票数量：触发时间为每次增加新订单后或者"""
        self.order_history.loc[
            (self.order_history.datetime.apply(lambda x: x.date() + timedelta(days=self.t)) <= current_time.date()) & (
                    self.order_history.order_type == ORDER_DIRECTION.BUY), "is_frozen"] = 0
        self.djsl = self.order_history.loc[self.order_history.is_frozen == 1, "volume"].sum()


class Papertest:
    """
    基于bar base的回测框架
    position 字典示例
    order 字典示例
    entrust 字典示例
    """

    def __init__(self,
                 initcash: int = 100000,
                 commisson: float = 0.0001,
                 tax_percent: float = 0.001,
                 t: int = 1):
        self.cash_available = initcash
        self.frozen_money = 0

        self.current_time = datetime(1999, 1, 1)
        self.position = dict()
        self.order = dict()

        self.commisson = commisson
        self.tax_percent = tax_percent
        self.t = t

        self.code_current_price = dict()
        self.return_history = list()

        self.settle_history = list()

    def get_today_profit(self):
        pass

    def get_all_profit(self):
        pass

    def all_order_done(self):
        """回测结束后的一些合并操作"""
        pass

    def settle(self):
        """
        结算
        1.
        合并持仓
        2. 计算当前回报
        3. 存储当前账户快照信息，包括仓位、总金额、可用金额等
        4.
        """
        settle_dict = {
            "datetime": self.current_time,
            "all_money": self.all_money,
            "cash_available": self.cash_available,
            "all_float_profit": self.all_float_profit,
            "position": [posii.settle() for codei, posii in self.get_current_position.items()]}
        self.settle_history.append(settle_dict)
        # print("settle: ", settle_dict)

    @property
    def order_hisotry_dataframe(self) -> pd.DataFrame:
        """获取订单历史的pandas DataFrame"""
        order_all = []
        for codei, position in self.position.items():
            order_all.append(position.order_history)
            for posi in position.old_history:
                order_all.append(posi)
        return pd.concat(order_all).sort_values("datetime").reset_index(drop=True)

    @property
    def all_money(self) -> float:
        return self.cash_available + self.frozen_money + self.positon_money

    @property
    def positon_money(self) -> float:
        """计算持仓当前价格"""
        return sum([posii.gpye * self.code_current_price[codei] for codei, posii in self.get_current_position.items()])

    @property
    def all_float_profit(self) -> float:
        """浮动盈亏"""
        return sum([posii.gpye * self.code_current_price[codei] - posii.cost_money
                    for codei, posii in self.get_current_position.items()])

    @property
    def get_current_position(self) -> dict:
        """获取当前持仓，取持仓股票余额大于0的票返回"""
        return {codei: posii for codei, posii in self.position.items() if posii.gpye > 0}

    def get_wait_order(self) -> dict:
        """获取未完成的订单"""
        return {codei: oderi for codei, oderi in self.order.items() if oderi.order_status == ORDER_STATUS.WAIT}

    def on_current_time(self, current_time):
        """账户时间更新、t+1状态更新、除权除息更新"""
        self.current_time = current_time
        # todo 除权除息账户修改
        for codei, posii in self.position.items():
            posii.cpt_djsl(self.current_time)

    def cpt_dividend(self, dividend_df: pd.DataFrame):
        pass

    def on_price_change(self, code, current_price):
        """更新股票当前价格-单个更新"""
        self.code_current_price[code] = current_price
        if code in self.position.keys():
            self.position[code].current_price = current_price

    def on_price_change_all(self, codeprice: pd.DataFrame):
        """更新股票当前价格-批量更新"""
        # todo
        pass

    def send_order(self,
                   code: str,
                   order_time: datetime,
                   order_price: float,
                   order_volume: int,
                   order_type: int = ORDER_DIRECTION.BUY,
                   ) -> str:
        """
        :param code: 代码
        :param order_time: 委托时间
        :param order_price: 委托价格
        :param order_volume: 委托量
        :param order_type: 买卖类型：类 ORDER_DIRECTION
        :return: order_id
        """
        order_id = str(uuid.uuid1())

        order_create = Paperorder(code=code,
                                  order_time=order_time,
                                  order_price=order_price,
                                  order_volume=order_volume,
                                  order_type=order_type,
                                  commisson=self.commisson,
                                  tax_percent=self.tax_percent,
                                  order_id=order_id
                                  )
        if order_type == ORDER_DIRECTION.BUY:
            order_frozen_money = order_create.order_price * order_create.order_volume * (1 + self.commisson)
            self.frozen_money += order_frozen_money
            self.cash_available -= order_frozen_money
        self.order[order_id] = order_create
        return order_id

    def make_deal(self, order_id, deal_volume: int = None, deal_price: float = None, deal_time: datetime = None):
        """成交订单"""
        if deal_volume is None:
            self.order[order_id].deal_volume = self.order[order_id].order_volume
        else:
            self.order[order_id].deal_volume = deal_volume

        if deal_price is None:
            self.order[order_id].deal_price = self.order[order_id].order_price
        else:
            self.order[order_id].deal_price = deal_price

        if deal_time is None:
            self.order[order_id].deal_time = self.order[order_id].order_time
        else:
            self.order[order_id].deal_time = deal_time

        if self.order[order_id].order_type == ORDER_DIRECTION.BUY:
            if self.order[order_id].code not in self.position.keys():
                self.position[self.order[order_id].code] = Paperpositon(code=self.order[order_id].code,
                                                                        t=self.t,
                                                                        code_type=MARKET.stock_cn)

            self.position[self.order[order_id].code].add_order(self.order[order_id], self.current_time)
            self.frozen_money -= self.order[order_id].frozen_money
            self.cash_available += self.order[order_id].frozen_money - self.order[order_id].deal_money

        elif self.order[order_id].order_type == ORDER_DIRECTION.SELL:
            self.position[self.order[order_id].code].add_order(self.order[order_id], self.current_time)
            self.cash_available += self.order[order_id].sell_money

        else:
            print("""订单未处理:""", order_id)
            return None

        # 订单状态完成
        self.order[order_id].order_status = ORDER_STATUS.DONE

    def cancel_deal(self, order_id):
        self.order[order_id].order_status = ORDER_STATUS.CANCEL


if __name__ == '__main__':
    pass
