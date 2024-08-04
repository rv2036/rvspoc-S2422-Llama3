赛题：Llama 3 在 K230 上的优化实现  
队伍名称：Kakaka  

K230开发板采用的是嘉楠科技Kendryte®系列AIoT芯片中的最新一代SoC芯片K230，该芯片采用全新的多异构单元加速计算架构，集成了2个RISC-V高能效计算核心。  
K230开发板可支持烧录多种固件，Linux+rtt双系统，rtt-only或者是Linux-only。由于板载DDR RAM只有512M，因此选用Linux-only系统镜像，通过设置swap空间保证Llama3模型能够正常运行。（镜像使用 https://kendryte-download.canaan-creative.com/developer/k230/canmv_debian_sdcard_sdk_1.3.img.gz）

根据题目的要求，选择使用llama.cpp（https://github.com/ggerganov/llama.cpp）进行模型推理。  


为了得到较好的运行效果，gguf文件使用Meta-Llama-3-8B.Q2_K.gguf（https://huggingface.co/QuantFactory/Meta-Llama-3-8B-GGUF/resolve/main/Meta-Llama-3-8B.Q2_K.gguf），并且使用了不同的toolchain，编译了不同的版本进行性能对比。

toolchain  
TAC GCC-900 toolchain：Xuantie-900-gcc-linux-6.6.0-glibc-x86_64-V2.10.1-20240712.tar.gz  
gcc toolchain：riscv64-glibc-ubuntu-22.04-gcc-nightly-2024.08.03-nightly.tar.gz  

编译准备工作：
```
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

修改Makefile文件，静态链接llama-cli文件
@@ -512,8 +512,8 @@ ifneq ($(filter loongarch64%,$(UNAME_M)),)
 endif
 
 else
-       MK_CFLAGS   += -march=rv64gcv -mabi=lp64d
-       MK_CXXFLAGS += -march=rv64gcv -mabi=lp64d
+       MK_CFLAGS   += -march=rv64gcv -mabi=lp64d -static
+       MK_CXXFLAGS += -march=rv64gcv -mabi=lp64d -static
 endif

设置环境变量（将TAC GCC-900 toolchain的路径加入环境变量）
```

编译版本1：
```
make RISCV_CROSS_COMPILE=1 RISCV=1 llama-cli -j
mv llama-cli run1

./run1 -m Meta-Llama-3-8B.Q2_K.gguf -p "Once upon a time, " -n 10
...
Once upon a time, 20 years ago, I would go to the movies
llama_print_timings:        load time =  483112.33 ms
llama_print_timings:      sample time =      28.65 ms /    10 runs   (    2.87 ms per token,   348.99 tokens per second)
llama_print_timings: prompt eval time =  373904.10 ms /     6 tokens (62317.35 ms per token,     0.02 tokens per second)
llama_print_timings:        eval time = 1169031.53 ms /     9 runs   (129892.39 ms per token,     0.01 tokens per second)
llama_print_timings:       total time = 1543507.21 ms /    15 tokens
```

编译版本2(尝试使用OpenBlas加速)：
```
根据官方文档（https://github.com/OpenMathLib/OpenBLAS）cross compile OpenBLAS && make PREFIX=<OpenBlasInstall> install
修改Makefile
-       MK_CPPFLAGS += -DGGML_USE_BLAS $(shell pkg-config --cflags-only-I openblas)
-       MK_CFLAGS   += $(shell pkg-config --cflags-only-other openblas)
-       MK_LDFLAGS  += $(shell pkg-config --libs openblas)
+       MK_CPPFLAGS += -DGGML_USE_BLAS $(shell pkg-config --cflags-only-I openblas) -I<OpenBlasInstall>/include
+       MK_CFLAGS   += $(shell pkg-config --cflags-only-other openblas) -I<OpenBlasInstall>/include
+       MK_LDFLAGS  += $(shell pkg-config --libs openblas) -L<OpenBlasInstall>/lib -lopenblas

make RISCV_CROSS_COMPILE=1 RISCV=1 GGML_OPENBLAS=1 llama-cli -j
mv llama-cli run2

./run2 -m Meta-Llama-3-8B.Q2_K.gguf -p "Once upon a time, " -n 10
...
Once upon a time, 40 years ago in fact, in a world where
llama_print_timings:        load time =  489615.65 ms
llama_print_timings:      sample time =      16.72 ms /    10 runs   (    1.67 ms per token,   598.12 tokens per second)
llama_print_timings: prompt eval time =  368072.39 ms /     6 tokens (61345.40 ms per token,     0.02 tokens per second)
llama_print_timings:        eval time = 1167444.37 ms /     9 runs   (129716.04 ms per token,     0.01 tokens per second)
llama_print_timings:       total time = 1536100.45 ms /    15 tokens
```

编译版本3(尝试使用RVV加速)：
```
设置环境变量（将gcc toolchain的路径加入环境变量）或手动修改rvv intrinsic

make RISCV_CROSS_COMPILE=1 RISCV=1 llama-cli -j
mv llama-cli run3

./run3 -m Meta-Llama-3-8B.Q2_K.gguf -p "Once upon a time, " -n 10
...
llama_print_timings:        load time =  451927.03 ms
llama_print_timings:      sample time =      23.84 ms /    10 runs   (    2.38 ms per token,   419.38 tokens per second)
llama_print_timings: prompt eval time =  147184.74 ms /     6 tokens (24530.79 ms per token,     0.04 tokens per second)
llama_print_timings:        eval time = 1152898.14 ms /     9 runs   (128099.79 ms per token,     0.01 tokens per second)
llama_print_timings:       total time = 1300673.63 ms /    15 tokens
```
