# rvspoc-S2422-Llama3
##Llama 3 在 K230 上的优化实现
Llama3模型模型规模较大，使用SD卡，使用swap的方式，成功在canmv_K230上运行Llama3(Q2，Q4和Q8量化)。
###############################环境准备######################################
##烧写镜像
使用嘉楠开发者社区提供镜像,镜像下载链接：https://developer.canaan-creative.com/resource， 镜像版本：canmv_debian_sdcard_sdk_1.3.img.gz

##安装软件
为了便于文件传输和重新分区，使用apt安装ssh和parted软件。注意在apt update前需要先同步一下系统时间。
参考命令：
1）更新时间：
date --set="2024-08-03 03:15:20" ##修改为UTC当前时间
2）apt update 
3）安装ssh：
apt install openssh-server -y
4）安装parted：
apt install parted -y

##重新分区

参考命令：
1）查看可用空间大小：
parted   -l /dev/mmcblk1
2）根据上条命令运行结果的SD卡大小提示设置分区；
parted /dev/mmcblk1 resizepart 3 62.5G
resize2fs /dev/mmcblk1p3
##设置swap
swap设置为2G
1）dd if=/dev/zero of=/mnt/swap bs=256M count=8
2）mkswap /mnt/swap
3）swapon /mnt/swap
###################程序运行#########################

试了两个llama3的实现，llama3.c 做了Q8量化，llama.cpp尝试Q2和Q4量化，具体如下：

1）基于https://github.com/jameswdelancey/llama3.c 实现，使用方法一致。需要生成q8量化文件。

##提交内容
运行需要三个文件：
llama3_8b_instruct_q80.bin 
下载地址：https://huggingface.co/Sophia957/llama3_8b_instruct_q80/resolve/main/llama3_8b_instruct_q80.bin
runq3-k230 （PR上传）
tokenizer.bin（PR上传）

其他：
a. 移植过程中，参考上届的llama2题目，在K230上对比了Llama2增加RVV前后的效果，提速明显，但尝试在llama3.c上增加rvv，没有明显提速且运行结果有点问题，于是尝试其他方法提速。
b. 由于Llama3中有较多的matmul计算，尝试使用Matrix进行提速，下载工具链：Xuantie-900-gcc-linux-6.6.0-glibc-x86_64-V2.10.1，编译Matrix的demo成功，但在K230中运行没有成功，提示指令不支持，后续查询C908资料没有看到包含Matrix相关介绍。


2）基于 https://github.com/ggerganov/llama.cpp 尝试了Q2_k和Q4_0

##提交内容
运行需要文件：
llama-cli-tune (PR上传)
model文件：Meta-Llama-3-8B.Q2_K.gguf 或 Meta-Llama-3-8B.Q4_0.gguf
下载地址：
https://huggingface.co/QuantFactory/Meta-Llama-3-8B-GGUF/resolve/main/Meta-Llama-3-8B.Q2_K.gguf
https://huggingface.co/QuantFactory/Meta-Llama-3-8B-GGUF/resolve/main/Meta-Llama-3-8B.Q4_0.gguf

参考运行命令：
./llama-cli-tune -m ./Meta-Llama-3-8B.Q2_K.gguf -p "Once upon a time, " -n 10   -s 123
./llama-cli-tune -m ./Meta-Llama-3-8B.Q4_0.gguf -p "Once upon a time, " -n 10   -s 123

其他：
a. llama.cpp中使用了rvv的intrinsic,但是目前使用 Xuantie-900-gcc-linux-6.6.0-glibc工具链，rvv intrinsic部分没有成功编译进去。


重启设备遇到网络启动失败，可运行下面指令：
networkctl
ip link set enu1 name eth0
systemctl restart networking.service


Submission repo for S2422. ref: rvspoc.org
