# 要求  
## 前端的逻辑   
1. 前端需要根据输入的仓库名和用户名，调用后端API，获取仓库和用户的信息。
2. 前端有3个参数，type, name, find
3. type: user 或 repo
4. name: 用户名或仓库名，如果type=repo，name=owner/repo。如果type=user，name=username
5. find：find repo 或 find user，分别对应2个按钮
6. 前端需要根据type，name和find，调用后端API，获取仓库和用户的信息。
7. username没有限制，owner/repo需要限制，owner和repo需要是合法的github仓库名

## 后端逻辑     
1. 后端需要根据前端返回的type，name和find，根据backend/recommend.py的代码逻辑，返回对应的数据。  

## 要求
1. 前后端的连接要正确
2. 前后端的数据格式要正确，保持一致
3. 请你根据backend/recommend.py的代码逻辑，在backend这个文件夹下给出后端API的代码
4. 重新部署后端API，并给出后端API的地址

