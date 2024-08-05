import nncase
import numpy as np
from nncase_base_func import *

def compile_kmodel(model_path, dump_path, calib_data):
    """
    Set compile options and ptq options.
    Compile kmodel.
    Dump the compile-time result to 'compile_options.dump_dir'
    """
    print("\n----------   compile    ----------")
    print("Simplify...")
    model_file = model_simplify(model_path)

    print("Set options...")
    # import_options
    import_options = nncase.ImportOptions()

    ############################################
    # 你需要修改下面这段代码中的参数来适配你的模型。
    # 详细的说明可以参考docs/USAGE_v2.md.
    ############################################
    # compile_options
    compile_options = nncase.CompileOptions()
    compile_options.target = "k230" #"cpu"
    compile_options.dump_ir = True  # if False, will not dump the compile-time result.
    compile_options.dump_asm = True
    compile_options.dump_dir = dump_path
    compile_options.input_file = "./Llama-3-onnx/llm_config.json"
    
    # preprocess args
    compile_options.preprocess = False
    if compile_options.preprocess:
        compile_options.input_type = "uint8" # "uint8" "float32"
        compile_options.input_shape = [1,224,320,3]
        compile_options.input_range = [0,1]
        compile_options.input_layout = "NHWC" # "NHWC"
        compile_options.swapRB = False
        compile_options.mean = [0,0,0]
        compile_options.std = [1,1,1]
        compile_options.letterbox_value = 0
        compile_options.output_layout = "NHWC" # "NHWC"

    # quantize options
    ptq_options = nncase.PTQTensorOptions()
    ptq_options.quant_type = "int8" # datatype : "float32", "int8", "int16"
    ptq_options.w_quant_type = "int8"  # datatype : "float32", "int8", "int16"
    ptq_options.calibrate_method = "NoClip" # "Kld"
    ptq_options.finetune_weights_method = "NoFineTuneWeights"
    ptq_options.dump_quant_error = False
    ptq_options.dump_quant_error_symmetric_for_signed = False

    # mix quantize options
    # more details in docs/MixQuant.md
    ptq_options.quant_scheme = ""
    ptq_options.quant_scheme_strict_mode = False
    ptq_options.export_quant_scheme = False
    ptq_options.export_weight_range_by_channel = False

    # dynamci
    shape_bucket_options = nncase.ShapeBucketOptions()
    shape_bucket_options.shape_bucket_enable = True 
    shape_bucket_options.shape_bucket_range_info = {"seq_len": [0, 128255], "history_len": [0, 256]}
    shape_bucket_options.shape_bucket_segments_count = 2
    ############################################
    
    ptq_options.samples_count = len(calib_data[0])
    ptq_options.set_tensor_data(calib_data)
    
    print("Compiling...")
    compiler = nncase.Compiler(compile_options)
    # import
    model_content = read_model_file(model_file)
    if model_path.split(".")[-1] == "onnx":
        compiler.import_onnx(model_content, import_options)
    elif model_path.split(".")[-1] == "tflite":
        compiler.import_tflite(model_content, import_options)
    
    compiler.use_ptq(ptq_options)
    
    # compile
    compiler.compile()
    kmodel = compiler.gencode_tobytes()
    
    kmodel_path = os.path.join(dump_path, "test.kmodel")
    with open(kmodel_path, 'wb') as f:
        f.write(kmodel)
    print("----------------end-----------------")
    return kmodel_path

if __name__ == '__main__':
    # compile kmodel multiple inputs
    model_path = "/root/autodl-tmp/Llama-3-onnx/llm.onnx"
    dump_path = "/root/autodl-tmp/Llama-3-kmodel/llm.kmodel"
    seqlen = 3
    history_len = 1
    # 校正集的数量为2
    calib_data =[[]]#np.random.randint[[(0, 128255, size=[seqlen,], dtype='int64'),np.random.randint(0, 128255, size=[seqlen,], dtype='int64')],[np.random.rand(1, 1, seqlen, seqlen).astype(np.float32),np.random.rand(1, 1, seqlen, seqlen).astype(np.float32)],[np.random.randint(0, seqlen-1, size=[1,seqlen], dtype='int64'),np.random.randint(0, seqlen-1, size=[1,seqlen], dtype='int64')],[np.random.rand(32, 2, 1, history_len, 8, 128).astype(np.float32),np.random.rand(32, 2, 1, history_len, 8, 128).astype(np.float32)]]
    kmodel_path = compile_kmodel(model_path, dump_path, calib_data)
