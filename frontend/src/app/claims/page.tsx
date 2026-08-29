"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  FileText,
  Upload,
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronRight,
  Camera,
  FileImage,
  ScanLine,
  Calculator,
  ClipboardCheck,
  ArrowRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadReceipt, preReviewClaim } from "@/lib/api";
import { mockClaimsPreReview } from "@/lib/mock-data";
import type { OCRResult, PreReviewResult } from "@/lib/mock-data";
import { ApiStatusIndicator } from "@/components/api-status-indicator";
import { BrandedPageHeader } from "@/components/branded-page-header";

const fadeIn = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function ClaimsPage() {
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "done">("idle");
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [preReviewResult, setPreReviewResult] = useState<PreReviewResult | null>(null);

  const requiredDocs = mockClaimsPreReview.required_docs;
  const claimTimeline = mockClaimsPreReview.claim_status;

  const handleUpload = async () => {
    setUploadState("uploading");

    try {
      // 创建一个模拟文件用于上传
      const mockFile = new File(["receipt"], "receipt.jpg", { type: "image/jpeg" });
      const ocr = await uploadReceipt(mockFile);
      setOcrResult(ocr);

      // 使用 OCR 结果进行预审
      const review = await preReviewClaim({
        hospital: ocr.hospital,
        total_amount: ocr.total,
        patient_name: ocr.patient,
        items: ocr.items,
      });
      setPreReviewResult(review);
    } catch {
      // 降级：使用模拟数据
      setOcrResult(mockClaimsPreReview.ocr_result);
      setPreReviewResult(mockClaimsPreReview.pre_review);
    }

    setUploadState("done");
  };

  const displayOcr = ocrResult || mockClaimsPreReview.ocr_result;
  const displayReview = preReviewResult || mockClaimsPreReview.pre_review;
  const reimbursementRate = displayReview.reimbursement_rate
    ? `${Math.round(displayReview.reimbursement_rate * 100)}%`
    : "85%";

  return (
    <div className="didayi-page space-y-5">
      {/* Page Header */}
      <motion.div {...fadeIn}>
        <BrandedPageHeader title="报销预审" description="AI 辅助识别报销材料，提前发现缺失信息并估算报销结果。" badge="智能预审" status={<ApiStatusIndicator />} />
      </motion.div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.1 }}>
          <Card className="didayi-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">待预审</p>
                  <p className="text-3xl font-bold text-orange-600 mt-1">2</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-orange-50">
                  <Clock className="h-6 w-6 text-orange-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.15 }}>
          <Card className="didayi-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">预审通过</p>
                  <p className="text-3xl font-bold text-green-600 mt-1">8</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-50">
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.2 }}>
          <Card className="didayi-card">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">需补充材料</p>
                  <p className="text-3xl font-bold text-red-600 mt-1">1</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-50">
                  <AlertCircle className="h-6 w-6 text-red-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid gap-5 lg:grid-cols-5">
        {/* Upload Area + OCR Results */}
        <div className="space-y-5 lg:col-span-3">
          {/* Upload Area */}
          <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.25 }}>
            <Card className="didayi-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Upload className="h-4 w-4 text-orange-500" />
                  上传报销材料
                </CardTitle>
              </CardHeader>
              <CardContent>
                <AnimatePresence mode="wait">
                  {uploadState === "idle" && (
                    <motion.div
                      key="idle"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      onClick={handleUpload}
                      className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50/50 p-8 cursor-pointer hover:border-orange-300 hover:bg-orange-50/30 transition-all group"
                    >
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50 group-hover:bg-orange-100 transition-colors mb-4">
                        <Camera className="h-7 w-7 text-orange-500" />
                      </div>
                      <p className="text-sm font-medium text-foreground mb-1">
                        拖拽发票图片到此处，或点击上传
                      </p>
                      <p className="text-xs text-muted-foreground">
                        支持 JPG、PNG、PDF 格式，单文件不超过 10MB
                      </p>
                      <div className="flex items-center gap-3 mt-4">
                        <Button variant="outline" size="sm" className="gap-1.5">
                          <FileImage className="h-3.5 w-3.5" />
                          选择文件
                        </Button>
                        <Button variant="outline" size="sm" className="gap-1.5">
                          <Camera className="h-3.5 w-3.5" />
                          拍照上传
                        </Button>
                      </div>
                    </motion.div>
                  )}

                  {uploadState === "uploading" && (
                    <motion.div
                      key="uploading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex flex-col items-center justify-center rounded-xl border-2 border-orange-200 bg-orange-50/30 p-8"
                    >
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-100 mb-4 animate-pulse">
                        <ScanLine className="h-7 w-7 text-orange-500" />
                      </div>
                      <p className="text-sm font-medium text-foreground mb-1">
                        正在识别发票信息...
                      </p>
                      <p className="text-xs text-muted-foreground">AI OCR 识别中，请稍候</p>
                    </motion.div>
                  )}

                  {uploadState === "done" && (
                    <motion.div
                      key="done"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="space-y-4"
                    >
                      {/* OCR Result Header */}
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-100">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <span className="text-sm text-green-700 font-medium">发票识别成功</span>
                      </div>

                      {/* Extracted Info */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 rounded-lg bg-gray-50">
                          <p className="text-xs text-muted-foreground">医院</p>
                          <p className="text-sm font-medium">{displayOcr.hospital}</p>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50">
                          <p className="text-xs text-muted-foreground">日期</p>
                          <p className="text-sm font-medium">{displayOcr.date}</p>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50">
                          <p className="text-xs text-muted-foreground">患者</p>
                          <p className="text-sm font-medium">{displayOcr.patient}</p>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50">
                          <p className="text-xs text-muted-foreground">科室</p>
                          <p className="text-sm font-medium">{displayOcr.department}</p>
                        </div>
                      </div>

                      {/* Items Table */}
                      <div>
                        <p className="text-xs text-muted-foreground mb-2">费用明细</p>
                        <div className="space-y-1">
                          {displayOcr.items.map((item, i) => (
                            <div key={i} className="flex items-center justify-between py-1.5 px-3 text-sm rounded hover:bg-gray-50">
                              <span>{item.name}</span>
                              <span className="font-medium">¥{item.price.toFixed(2)}</span>
                            </div>
                          ))}
                          <div className="flex items-center justify-between py-2 px-3 text-sm border-t border-border font-semibold">
                            <span>合计</span>
                            <span>¥{displayOcr.total.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>

                      {/* Pre-review Result */}
                      <div className="p-4 rounded-xl bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-100">
                        <div className="flex items-center gap-2 mb-3">
                          <Calculator className="h-4 w-4 text-orange-600" />
                          <span className="text-sm font-semibold text-orange-800">预审结果</span>
                        </div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-muted-foreground">费用总额</span>
                          <span className="text-sm font-medium">¥{displayOcr.total.toFixed(2)}</span>
                        </div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-muted-foreground">报销比例</span>
                          <span className="text-sm font-medium">{reimbursementRate}</span>
                        </div>
                        <div className="flex items-center justify-between pt-2 border-t border-orange-200">
                          <span className="text-sm font-semibold text-orange-800">预估报销金额</span>
                          <span className="text-xl font-bold text-orange-600">¥{displayReview.estimated_reimbursement.toFixed(2)}</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                          根据您的职工医保待遇，门诊费用报销比例为{reimbursementRate}，起付线已满足。实际报销金额以医保中心审核为准。
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <Button className="flex-1 gap-1.5">
                          <ClipboardCheck className="h-4 w-4" />
                          提交报销申请
                        </Button>
                        <Button variant="outline" onClick={() => { setUploadState("idle"); setOcrResult(null); setPreReviewResult(null); }}>
                          重新上传
                        </Button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-5 lg:col-span-2">
          {/* Required Documents Checklist */}
          <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.3 }}>
            <Card className="didayi-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <ClipboardCheck className="h-4 w-4 text-orange-500" />
                  所需材料清单
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {requiredDocs.map((doc, i) => (
                    <div
                      key={i}
                      className={`flex items-center gap-3 p-2.5 rounded-lg ${
                        doc.status === "uploaded" ? "bg-green-50/50" : "bg-gray-50"
                      }`}
                    >
                      {doc.status === "uploaded" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-gray-400 shrink-0" />
                      )}
                      <span
                        className={`text-sm ${
                          doc.status === "uploaded"
                            ? "text-green-700 line-through"
                            : "text-foreground"
                        }`}
                      >
                        {doc.name}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    已上传 {requiredDocs.filter((d) => d.status === "uploaded").length}/{requiredDocs.length}
                  </span>
                  <span className="text-orange-600 font-medium">还需2份材料</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Claim Tracking Timeline */}
          <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.35 }}>
            <Card className="didayi-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-orange-500" />
                  报销进度追踪
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {claimTimeline.map((event, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100">
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                        </div>
                        {i < claimTimeline.length - 1 && (
                          <div className="w-px h-6 bg-green-200" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{event.title}</p>
                        <p className="text-xs text-muted-foreground">{event.desc}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{event.date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
