"""接口定义层（API Object）：按被测业务模块分子目录。

每个模块一个子目录：apis/{模块}/{模块}_api.py
模块按被测对象划分（例如订单模块 apis/order/order_api.py）。

约定：
  - 用例只调用本层函数，不拼 URL、不直接组装请求体
  - 接口路径与默认参数集中在此，接口变更只改一处
  - 参考实现可复制 api-automation-template/apis/example/example_api.py
"""
