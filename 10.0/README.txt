
基于官方Docker修改，修复或增强以下功能：


1、升级xlrd到1.0.0版，以解决导入excel文件时中文出错（UnicodeEncodeError: 'ascii' codec can't encode characters in position...）
升级办法：
在Docker中第22行
  && pip install psycogreen==1.0
后面增加
  && pip install xlrd=1.0.0


