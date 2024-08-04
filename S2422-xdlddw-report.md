# S2422 Competition Report 
## 队名:xdlddw  成员:Xingke Jiangwenyuan

- 比赛完成情况：
- 在搭载了 K230 的 RISC-V 开发板上，移植大语言模型 Llama 3，并正确运行  【完成】
- 使用 RISC-V Vector （或 Xuantie Matrix）扩展指令集对 LLaMA 3 的实现进行优化，加速模型的执行速度。  【受限于k230内存和io的性能，RVV优化实现的意义不大】

## 参考资料
- 参考官方资料
[编译k230 sdk]: https://developer.canaan-creative.com/k230/dev/zh/CanMV_K230_%E6%95%99%E7%A8%8B.html
，编译K230最新版的sdk。

- 参考
[llama.cpp]: https://github.com/ggerganov/llama.cpp
对llama3进行量化和交叉编译，将llama3量化后的模型在k230大核上推理。

- 参考llm-export[llm-export]: https://github.com/wangzhaode/llm-export
，将llama3转成onnx格式，并尝试转成kmodel格式在K230大核上进行推理。（未成功）


## 方法1：使用Llama.cpp完成部署
- 对Llama.cpp进行交叉编译，可直接运行在K230的大核上。
- 在运行llama_cli程序的llama_cpp_main.log日志里CPU compute buffer size =   560.01 MiB > 512MB（内存），也就是K230的内存放不下llama的权重矩阵，需要增加swap内存才能推理，这样会极大的影响推理的速度。

### 1、编译K230 sdk
- 参考官方手册，编译并运行docker环境
```
git clone https://gitee.com/kendryte/k230_sdk.git
cd k230_sdk
source tools/get_download_url.sh && make prepare_sourcecode
docker build -f tools/docker/Dockerfile -t k230_docker tools/docker
docker run -u root -it -v $(pwd):$(pwd) -v $(pwd)/toolchain:/opt/toolchain -w $(pwd) k230_docker /bin/bash
```
- 调整config文件使linux在大核上运行
- 调整sharefs文件为5G
- 编译CANMV-K230板子镜像
```
make CONF=k230_canmv_defconfig
```

### 2、编译llama.cpp
- 下载llama.cpp源码
```
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && vim Makefile
```
- 修改 makefile里面的CC为自己的路径
```
ifdef RISCV_CROSS_COMPILE
CC      := /home/xingke/desktop/k230_sdk/toolchain/Xuantie-900-gcc-linux-5.10.4-glibc-x86_64-V2.6.0/bin/riscv64-unknown-linux-gnu-gcc
CXX     := /home/xingke/desktop/k230_sdk/toolchain/Xuantie-900-gcc-linux-5.10.4-glibc-x86_64-V2.6.0/bin/riscv64-unknown-linux-gnu-g++
```
- 交叉编译llama.cpp
```
make RISCV=1 RISCV_CROSS_COMPILE=1 LLAMA_STATIC=1 LLAMA_NO_OPENMP=1
```

### 3、库名移植
-  将k230__sdk的库名和llama.cpp库名对齐
```
ln -s /lib64xthead/lp64d/ld-2.33.so /lib/ld-linux-riscv64-lp64d.so.1
```

### 4、测试
- 将llama.cli和量化好的q4模型拷贝到sharefs中
- matmult测试
```
./llama-benchmark-matmult
```
- 最简单的矩阵乘法需要763.12MB的内存，所以对512MB内存的K230来说，运行llama3，内存偏小。
- llama-cli 测试（Q4）
```
./llama-cli -m Llama-3-7B.Q4_K_S.gguf -p "I believe the meaning of life is" -n 128
- prompt eval time = 51.9s/per token
- eval time = 170s/per token
```

- llama-cli 测试（Q2）
```
./llama-cli -m ggml-model-q2_k.gguf -p "I believe the meaning of life is" -n 128
- prompt eval time = 65.5s/per token
- eval time = 179s/per token
```

- 因为使用了swap交换内存进行扩容，所以推理的速度还是比较慢的。


## 方法2：使用nncase完成部署

### 1、环境选择
- 因为转换30G的llama3模型文件需要200G左右的内存，这里选择了autodl的环境，Python  3.8(ubuntu20.04)，240G内存的镜像。

### 2、配置虚拟环境myenv并下载llm-export
```
conda config --set ssl_verify no
conda create -n myenv python=3.9
git clone https://github.com/wangzhaode/llm-export.git
pip install -r requirements
pip install --upgrade onnxruntime
pip install transformers==4.40.0
```

### 3、安装 nncase (这里是自动配置的nncase 2.9.0、dotnet7.0)
```
pip install --upgrade pip
pip install nncase
pip install nncase-kpu 
pip install onnxsim scikit-learn
wget https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt update
sudo apt install -y apt-transport-https
sudo apt install -y dotnet-sdk-7.0
```

### 4、将llama3 转换成onnx
- git 下载Llama-3-8B-Instruct库，并重新命名为Llama-3 
```
python llm_export.py --path ../Llama-3 --type Llama-3-8B-Instruct --onnx_path ../Llama-3-onnx --export_test --test TEST --export
```
会生成30G的llama3.onnx文件以及llm_config.json

### 5、将onnx文件转成kmodel
- 编写compile_model.py脚本，将30G的llama3.onnx转成kmodel，并参考了[shape_bucket]文档：
https://github.com/kendryte/nncase/blob/0e8dabdb5a3cfec5474eee62900bd392fc7432f9/docs/shape_bucket.md#L4
增加了shape_bucket_options选项，可惜的是没有转换成功
- nncase2.9.0应该是只支持转换2GB的模型。
