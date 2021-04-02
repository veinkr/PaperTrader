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


class Paperpositon:
    """
    order_history 样例
    [(1,15.6,200,,2020-03-31 09:54:16)]
    """

    def __init__(self,
                 code: str,
                 code_type: str = "stock_cn",
                 t: int = 1,  # t+1
                 ):
        self.code = code
        self.code_type = code_type  # 预留，处理期货时算法与A股不一致
        self.t = t
        self.cbj = None
        self.gpye = 0
        self.djsl = 0
        self.order_history = pd.DataFrame(
            columns=["order_id", "direction", "price", "volume", "commission", "tax", "is_frozen",
                     "datetime"])  # 当平仓时候，volume为负数
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

    def add_order(self, order_info):
        self.order_history.append(order_info, ignore_index=True)
        self.cpt_current()

    def cpt_current(self):
        """计算当前仓位的成本价喝持仓数量喝可用金额等"""
        global current_time
        if self.code_type == "stock_cn":
            self.gpye = self.order_history.volume.sum()
            if self.gpye == 0 and self.order_history.shape[0] > 0:
                self.old_history.append(self.order_history)
                self.order_history = pd.DataFrame(columns=["order_id", "direction", "price", "volume",
                                                           "commission", "tax", "datetime"])
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


class Paperaccount:
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
        self.current_time = datetime(1999, 1, 1)
        self.frozen_money = 0
        self.position = dict()
        self.order = dict()
        self.entrust = dict()
        self.return_history = list()
        self.commisson = commisson
        self.tax = tax
        self.t = t
        self.code_current_price = dict()

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
        return 0  # todo 计算

    @property
    def fudongyinkui(self):
        """浮动盈亏"""
        return

    def on_price_change(self, code, current_price):
        """更新股票当前价格code_current_price"""
        self.code_current_price[code] = current_price

    def send_order(self,
                   code,
                   trade_time,
                   trade_price: float,
                   trade_amount: int,
                   trade_towards: int,
                   trade_type: int = 1,
                   order_id=str(uuid.uuid1()),
                   trade_id=str(uuid.uuid1())):
        """
        :param code: 代码
        :param trade_time: 委托时间
        :param trade_price: 委托价格
        :param trade_amount: 委托量
        :param trade_towards: 买卖方向:1：开，0：平
        :param trade_type: 买卖类型：1：多单 0：空单 默认为1
        :param order_id:uuid
        :param trade_id:uuid
        :return:
        """
        order_create = {"code": code,
                        "order_time": trade_time,
                        "order_price": trade_price,
                        "order_amount": trade_amount,
                        "order_towards": trade_towards,
                        "order_type": trade_type,
                        "order_id": order_id,
                        "trade_id": trade_id,
                        "frozen_buy": trade_price * trade_amount,
                        "frozen_commisson": trade_price * trade_amount * self.commisson,
                        "status": 0}

        self.frozen_money += order_create["frozen_money"]
        self.cash_available -= order_create["frozen_money"]
        self.entrust[order_create["order_id"]] = order_create
        return order_create["order_id"]

    def make_deal(self, order_id, deal_price: float = None):
        """"""
        order_success = self.entrust[order_id]
        if deal_price is None:
            order_success["deal_price"] = order_success["order_price"]
        else:
            order_success["deal_price"] = deal_price

        if order_success["order_towards"] == 1 & order_success["order_type"] == 1:
            if order_success["code"] in self.position.keys():
                # todo 更新订单
                self.position[order_success["code"]].add_order(self.deal_to_position(order_success))
            else:
                # todo 新增订单
                self.position[order_success["code"]] = Positon(code=order_success["code"])
                self.position[order_success["code"]].add_order(self.deal_to_position(order_success))

        elif order_success["order_towards"] == 0 & order_success["order_type"] == 1:
            self.position[order_success["code"]].add_order(self.deal_to_position(order_success))
            # todo 账户余额变化
            # todo 扣印花税操作
        else:
            print("订单未处理")
            pass

    @staticmethod
    def deal_to_position(deal_dict: dict) -> dict:
        """
        转换deal字典为positon字典
        :param deal_dict: 委托字典
        """
        return deal_dict

    def get_current_position(self):
        """获取当前持仓，取持仓股票余额大于0的票返回"""


if __name__ == '__main__':
    current_time = datetime(1999, 1, 1)

    pass
