# Git仓库初始化指南

本指南将帮助您将FS服装搭配专家项目提交到Git仓库。

## 步骤1：初始化Git仓库

在项目目录中打开命令行终端，执行以下命令：

```bash
# 初始化Git仓库
git init

# 查看当前状态
git status
```

## 步骤2：创建.gitignore文件

为了避免将不必要的文件提交到仓库，创建一个.gitignore文件：

```bash
# 创建.gitignore文件
New-Item -Path ".gitignore" -ItemType "file" -Value 'bin/
obj/
*.user
*.suo
*.csproj.user
*.cache
*.vs/
.vs/
*.swp
*.swo
*~
.DS_Store
Thumbs.db
'
```

## 步骤3：添加文件到暂存区

```bash
# 添加所有文件到暂存区
git add .

# 查看添加状态
git status
```

## 步骤4：提交初始版本

```bash
# 提交初始版本
git commit -m "初始化项目：FS服装搭配专家v1.0"

# 查看提交历史
git log
```

## 步骤5：创建远程仓库（可选）

如果您想将项目推送到远程仓库（如GitHub、Gitee等），请按照以下步骤操作：

### 在GitHub上创建仓库

1. 登录GitHub
2. 点击右上角的"+"按钮，选择"New repository"
3. 填写仓库名称（如"FS服装搭配专家"）
4. 选择仓库类型（公开或私有）
5. 点击"Create repository"

### 关联本地仓库与远程仓库

```bash
# 添加远程仓库（将YOUR_USERNAME替换为您的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/FS服装搭配专家.git

# 查看远程仓库信息
git remote -v
```

## 步骤6：推送到远程仓库

```bash
# 推送到远程仓库
git push -u origin master
```

## 步骤7：验证推送结果

打开GitHub仓库页面，验证文件是否已成功推送。

## 后续操作

### 提交新更改

当您对项目进行更改后，可以按照以下步骤提交：

```bash
# 添加更改的文件
git add .

# 提交更改
git commit -m "描述您的更改"

# 推送到远程仓库
git push
```

### 分支管理

如果您需要创建分支进行开发：

```bash
# 创建并切换到新分支
git checkout -b feature/new-feature

# 在新分支上进行开发和提交

# 切换回主分支
git checkout master

# 合并分支
git merge feature/new-feature
```

## 常见问题

### 1. 推送失败

如果推送失败，可能是因为远程仓库有您本地没有的更改。解决方法：

```bash
# 拉取远程更改
git pull

# 解决冲突（如果有）

# 再次推送
git push
```

### 2. 忘记添加.gitignore文件

如果您忘记添加.gitignore文件，可以在添加后移除已提交的不必要文件：

```bash
# 添加.gitignore文件
git add .gitignore

git commit -m "添加.gitignore文件"

# 移除已提交的不必要文件
git rm -r --cached bin/ obj/

git commit -m "移除不必要的文件"

# 推送到远程仓库
git push
```

## 总结

通过以上步骤，您已经成功将FS服装搭配专家项目提交到Git仓库。Git将帮助您跟踪代码更改，方便团队协作和版本管理。

祝您开发顺利！
