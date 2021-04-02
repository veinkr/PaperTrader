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

order_history_temple = pd.DataFrame(columns=["order_id", "order_type", "price", "volume",
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
    BUY 股票 买入
    SELL 股票 卖出
    BUY_OPEN 期货 多开
    BUY_CLOSE 期货 空平(多头平旧仓)
    SELL_OPEN 期货 空开
    SELL_CLOSE 期货 多平(空头平旧仓)
    ASK  申购
    """

    WAIT = 0
    DONE = 1


class MARKET:
    stock_cn = "stock_cn"
    index_cn = "index_cn"


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
        self.status = ORDER_STATUS.WAIT

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
        positon_dict = {"order_id": self.order_id,
                        "order_type": self.order_type,
                        "price": self.deal_price,
                        "volume": self.deal_volume if self.order_type in [ORDER_DIRECTION.BUY] else self.deal_volume * (
                            -1),
                        "commission": self.deal_commisson,
                        "tax": self.deal_tax,
                        "datetime": self.deal_time}
        return positon_dict


class Paperpositon:
    """
    order_history 样例
    [(1,15.6,200,,2020-03-31 09:54:16)]
    """

    def __init__(self,
                 code: str,
                 t: int,  # t+1
                 code_type: str,
                 ):
        self.code = code
        self.code_type = code_type  # 预留，处理期货时算法与A股不一致
        self.t = t
        self.cbj = None
        self.gpye = 0
        self.djsl = 0
        self.current_price = None
        self.order_history = order_history_temple  # 当平仓时候，volume为负数
        self.old_history = list()

    def __repr__(self):
        return {"code": self.code,
                "cbj": self.cbj,
                "gpye": self.gpye,
                "djsl": self.djsl,
                "kyye": self.kyye,
                "order_history": self.order_history.to_dict(orient='records'),
                }

    @property
    def kyye(self):
        return self.gpye - self.djsl

    def add_order(self, order_info: Paperorder, current_time: datetime):
        self.order_history.append(order_info.order_position, ignore_index=True)
        self.cpt_current(current_time)

    def cpt_current(self, current_time):
        """计算当前仓位的成本价喝持仓数量喝可用金额等"""
        if self.code_type == "stock_cn":
            self.gpye = self.order_history.volume.sum()
            if self.gpye == 0 and self.order_history.shape[0] > 0:
                self.old_history.append(self.order_history)
                self.order_history = order_history_temple
                self.djsl = 0
                self.cbj = None
            elif self.gpye > 0 and self.order_history.shape[0] > 0:
                self.djsl = self.order_history.loc[(self.order_history.datetime.apply(
                    lambda x: x.date() >= current_time.date() + timedelta(days=self.t))) & (
                                                           self.order_history.direction == 1), "volume"].sum()
                self.cbj = self.order_history.apply(lambda row: row.price * row.volume - row.commission,
                                                    axis=1).sum() / self.gpye
            else:
                pass


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
                 tax: float = 0.001,
                 t: int = 1):
        self.cash_available = initcash
        self.frozen_money = 0

        self.current_time = datetime(1999, 1, 1)
        self.position = dict()
        self.order = dict()

        self.commisson = commisson
        self.tax = tax
        self.t = t

        self.code_current_price = dict()
        self.return_history = list()

    def get_today_profit(self):
        pass

    def get_all_profit(self):
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
        pass

    @property
    def all_money(self):
        return self.cash_available + self.frozen_money + self.positon_money

    @property
    def positon_money(self):
        """计算持仓当前价格"""
        return sum([posii.gpye * self.code_current_price[codei] for codei, posii in self.get_current_position.items()])

    @property
    def all_float_profit(self):
        """浮动盈亏"""
        return sum([posii.gpye * (self.code_current_price[codei] - posii.cbj)
                    for codei, posii in self.get_current_position.items()])

    @property
    def get_current_position(self):
        """获取当前持仓，取持仓股票余额大于0的票返回"""
        return {codei: posii for codei, posii in self.position.items() if posii.kyye > 0}

    def get_wait_order(self):
        """获取未完成的订单"""
        return {codei: oderi for codei, oderi in self.order.items() if oderi.order_status == ORDER_STATUS.WAIT}

    def on_current_time(self, current_time):
        """账户时间更新"""
        self.current_time = current_time
        # todo 持仓状态刷新（ t+1冻结数量修改）
        # todo 除权除息账户修改
        for codei, posii in self.position.items():
            posii.cpt_current(self.current_time)

    def on_price_change(self, code, current_price):
        """更新股票当前价格-单个更新"""
        self.code_current_price[code] = current_price

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
                   ):
        """
        :param code: 代码
        :param order_time: 委托时间
        :param order_price: 委托价格
        :param order_volume: 委托量
        :param order_type: 买卖类型：类 ORDER_DIRECTION
        :return:
        """
        order_id = str(uuid.uuid1())

        order_create = Paperorder(code=code,
                                  order_time=order_time,
                                  order_price=order_price,
                                  order_volume=order_volume,
                                  order_type=order_type,
                                  commisson=self.commisson,
                                  tax=self.tax,
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
            print(f"""订单未处理:{order_id}""")
            return None

        # 订单状态完成
        self.order[order_id].order_status = ORDER_STATUS.DONE


if __name__ == '__main__':
    # current_time = datetime(1999, 1, 1)

    pass
