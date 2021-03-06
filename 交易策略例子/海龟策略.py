# 导入函数库
from jqdata import *
import numpy

def initialize(context):
    set_params()        #1设置策参数
    set_variables()     #2设置中间变量
    set_backtest()      #3设置回测条件
    run_daily(daily, time='every_bar')

#1
#设置策略参数
def set_params():
    g.security = '000063.XSHE'
    # 系统入市的trailing date
    g.short_in_date = 20
    # 系统 exiting market trailing date
    g.short_out_date = 10
    # 系统2 exiting market trailing date
    # g.dollars_per_share是标的股票每波动一个最小单位，1手股票的总价格变化量。
    # 在国内最小变化量是0.01元，所以就是0.01×100=1
    g.dollars_per_share = 1
    # 可承受的最大损失率
    g.loss = 0.1
    # 若超过最大损失率，则调整率为：
    # 计算N值的天数
    g.number_days = 20
    # 最大允许单元
    g.unit_limit = 4
    # 系统1所配金额占总金额比例

#2

#4 根据不同的时间段设置滑点与手续费
def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(FixedSlippage(0)) 
    # 根据不同的时间段设置手续费
    dt=context.current_dt
#设置中间变量
def set_variables():
    # 初始单元
    g.unit = 1000
    # 存储N值
    g.N = []
    # 系统1的突破价格
    g.break_price = 0
    # 系统2的突破价格
    g.sys = 0
    #存储唐奇安通道上轨
    g.high=[]
    #用来存储唐奇安通道下轨
    g.low=[]

#3
#设置回测条件
def set_backtest():
    # 作为判断策略好坏和一系列风险值计算的基准
    set_benchmark(g.security)
    set_option('use_real_price',True) #用真实价格交易
    log.set_level('order','error') # 设置报错等级

'''
================================================================================
每天开盘前
================================================================================
'''
#每天开盘前要做的事情
def before_trading_start(context):
    set_slip_fee(context) #设置交易费率
    calculate_N()#计算N
    tqatds()#计算唐奇安通道上轨
    tqatdx()#计算唐奇安通道下轨
    #设置费率
    dt=context.current_dt
    if dt>datetime.datetime(2013,1, 1):
        set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5)) 
        
    elif dt>datetime.datetime(2011,1, 1):
        set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))
            
    elif dt>datetime.datetime(2009,1, 1):
        set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))
                
    else:
        set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))
    
'''
================================================================================
每天交易时
================================================================================
'''
# 按分钟回测
def daily(context):
    #获取当前分钟的价格
    price=attribute_history(g.security, 1, '1m', 'close')
    current_price=price['close'][-1]
    #获取当前账户的价值和资金
    value=context.portfolio.portfolio_value
    cash=context.portfolio.cash
    Dollar_Volatility=g.N[-1]*1
    g.unit=value*0.0/Dollar_Volatility#当前波动率下，最大单次损失1%的购买量
    if g.sys==0:
        market_in(context,current_price,g.short_in_date)#开仓买入
    else:
        stop_loss(current_price)#止损
        market_add(context,current_price,g.short_in_date)#加仓
        market_out(current_price, g.short_out_date)#出局
            
 #唐奇安通道上轨
def tqatds():
    price=attribute_history(g.security,20,'1d',('high','low','close'))
    g.high.append(max(price['high']))
    return g.high
#唐奇安通道下轨    
def tqatdx():
    price=attribute_history(g.security,20,'1d',('high','low','close'))
    g.low.append(min(price['low']))
    return g.low
#计算N    
def calculate_N():
    if len(g.N)==0:
        price=attribute_history(g.security,21,'1d',('high','low','close'))
        st1=[]
        for i in range(1,21):
            hl=price['high'][i]-price['low'][i]
            hc=price['high'][i]-price['close'][i-1]
            cl=price['close'][i-1]-price['low'][i]
            True_Range=max(hl,hc,cl)
            st1.append(True_Range)
        current_N=round(np.mean(np.array(st1)),3)
        g.N.append(current_N)
    else:
        price = attribute_history(g.security, 2, '1d',('high','low','close'))
        hl = price['high'][-1]-price['low'][-1]
        hc = price['high'][-1]-price['close'][-2]
        cl = price['close'][-2]-price['low'][-1]
         # Calculate the True Range
        True_Range = max(hl, hc, cl)
        # 计算前g.number_days（大于20）天的True_Range平均值，即当前N的值：
        current_N = round((True_Range + (g.number_days-1)*(g.N)[-1])/g.number_days,3)
        (g.N).append(current_N)

#开仓买入
def market_in(context,current_price,in_date):
    price=attribute_history(g.security,in_date,'1d', 'close')
    # 当前价格突破唐奇安通道上轨
    if current_price > g.high[-1]:
        cash=context.portfolio.available_cash
        #计算当前可买量
        num_of_shares=cash/current_price
        if num_of_shares>=g.unit and g.sys<int(g.unit_limit*g.unit):
            log.info('SYS买入',g.unit)
            order(g.security,int(g.unit))
            g.sys+=int(g.unit)
            g.break_price=current_price
 
 #加仓                   
def market_add(context,current_price,in_date):
   #当前价格大于上市买入价格的0.5个N
    if current_price>=g.break_price+0.5*g.N[-1]:
        cash=context.portfolio.available_cash
        num_of_shares=cash/current_price
        if num_of_shares>=g.unit and g.sys<int(g.unit_limit*g.unit):
            log.info('g.sys加仓{}:{}'.format(g.security,current_price))
            order(g.security,int(g.unit))
            g.sys+=int(g.unit)
            g.break_price=current_price
#出局
def market_out(current_price,out_date):
    price=attribute_history(g.security,out_date,'1d',('close','low'))
    #当前价格低于唐奇安通道下轨
    if current_price<g.low[-1] and g.sys>0:
        log.info('SYS离场')
        order_target(g.security, 0)
        g.sys=0
#止损                        
def stop_loss(current_price):
    #价格距离最后买入价格回调2个单位的波动
    if current_price<g.break_price-2*g.N[-1]:
        log,info('SYS止损')
        order_target(g.security, 0)
        g.sys=0
