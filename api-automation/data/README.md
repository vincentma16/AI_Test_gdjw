一个被测模块一个子目录与数据文件：
  data/<模块>/<模块>.yaml

敏感值写 ${VAR} 占位，真实值放 .env；在用例或 apis 层加载时用
common.config.expand_env 展开。
