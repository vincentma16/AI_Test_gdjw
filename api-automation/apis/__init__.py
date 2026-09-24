"""接口定义层（API Object）：按业务模块分子目录。

每个业务模块一个子目录：apis/{模块}/{模块}_api.py
模块按业务实体划分：account / staff / client / house / lead / deal ...

用例只调用本层函数，不拼 URL、不直接组装请求体。
接口路径/默认参数集中在此，变更只改一处。
"""