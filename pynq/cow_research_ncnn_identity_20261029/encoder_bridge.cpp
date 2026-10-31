#include "net.h"
#include <cstring>
#include <exception>
#include <string>

namespace {
thread_local std::string last_error;
struct Encoder { ncnn::Net net; };
}
extern "C" {
const char* cow_ncnn_error() { return last_error.c_str(); }
void* cow_ncnn_create(const char* param, const char* weights, int threads) {
    try {
        auto* e = new Encoder;
        e->net.opt.num_threads = threads;
        e->net.opt.use_vulkan_compute = false;
        e->net.opt.use_fp16_packed = false;
        e->net.opt.use_fp16_storage = false;
        e->net.opt.use_fp16_arithmetic = false;
        e->net.opt.use_bf16_storage = false;
        if (e->net.load_param(param) || e->net.load_model(weights)) {
            delete e; last_error = "NCNN model load failed"; return nullptr;
        }
        return e;
    } catch (const std::exception& e) { last_error = e.what(); return nullptr; }
}
int cow_ncnn_run(void* handle, const float* input, float* output) {
    try {
        auto* e = static_cast<Encoder*>(handle);
        if (!e || !input || !output) return -1;
        ncnn::Mat x(224, 224, 3);
        for (int c = 0; c < 3; ++c)
            std::memcpy(x.channel(c), input + c * 224 * 224, 224 * 224 * sizeof(float));
        auto extractor = e->net.create_extractor();
        if (extractor.input("in0", x)) return -2;
        ncnn::Mat y;
        if (extractor.extract("out0", y)) return -3;
        if (y.elempack != 1 || y.elemsize != sizeof(float) || y.total() != 576) {
            last_error = "Expected576FP32outputvalues"; return -4;
        }
        std::memcpy(output, y, 576 * sizeof(float));
        return 0;
    } catch (const std::exception& e) { last_error = e.what(); return -9; }
}
void cow_ncnn_destroy(void* handle) { delete static_cast<Encoder*>(handle); }
}
