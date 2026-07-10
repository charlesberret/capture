"""Apple Vision OCR provider."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class AppleVisionProvider:
    def __init__(self, provider_cfg: dict):
        self.cfg = provider_cfg

    def extract(self, filepath: Path) -> str | None:
        return _ocr_image(filepath, self.cfg)


def _ocr_image(filepath: Path, cfg: dict) -> str | None:
    try:
        import Quartz
        from Foundation import NSURL
        import Vision

        image_url = NSURL.fileURLWithPath_(str(filepath))
        image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)
        if not image_source:
            return None

        cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)
        if not cg_image:
            return None

        request = Vision.VNRecognizeTextRequest.alloc().init()
        level = cfg.get("recognition_level", "accurate")
        if level == "fast":
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
        else:
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(cfg.get("language_correction", True))

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
        success = handler.performRequests_error_([request], None)
        if not success:
            return None

        results = request.results()
        if not results:
            return None

        return "\n".join(obs.topCandidates_(1)[0].string() for obs in results)

    except Exception as e:
        print(f"Vision OCR failed: {e}")
        return None


def ocr_pdf(filepath: Path) -> str | None:
    try:
        import Quartz
        from Foundation import NSURL
        import Vision

        pdf_url = NSURL.fileURLWithPath_(str(filepath))
        pdf_doc = Quartz.CGPDFDocumentCreateWithURL(pdf_url)
        if not pdf_doc:
            print(f"  Could not open PDF: {filepath}")
            return None

        page_count = Quartz.CGPDFDocumentGetNumberOfPages(pdf_doc)
        print(f"  PDF has {page_count} page(s)")
        all_text: list[str] = []

        for page_num in range(1, page_count + 1):
            page = Quartz.CGPDFDocumentGetPage(pdf_doc, page_num)
            if not page:
                continue

            media_box = Quartz.CGPDFPageGetBoxRect(page, Quartz.kCGPDFMediaBox)
            width = int(media_box.size.width * 2)
            height = int(media_box.size.height * 2)

            color_space = Quartz.CGColorSpaceCreateDeviceRGB()
            context = Quartz.CGBitmapContextCreate(
                None, width, height, 8, width * 4, color_space, Quartz.kCGImageAlphaPremultipliedLast
            )
            Quartz.CGContextSetRGBFillColor(context, 1, 1, 1, 1)
            Quartz.CGContextFillRect(context, Quartz.CGRectMake(0, 0, width, height))
            Quartz.CGContextScaleCTM(context, 2, 2)
            Quartz.CGContextDrawPDFPage(context, page)
            cg_image = Quartz.CGBitmapContextCreateImage(context)

            if cg_image:
                request = Vision.VNRecognizeTextRequest.alloc().init()
                request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
                request.setUsesLanguageCorrection_(True)
                handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
                success = handler.performRequests_error_([request], None)
                if success and request.results():
                    page_text = [obs.topCandidates_(1)[0].string() for obs in request.results()]
                    if page_text:
                        if page_count > 1:
                            all_text.append(f"[Page {page_num}]")
                        all_text.extend(page_text)
                        print(f"  Page {page_num}: {len(page_text)} lines")

        return "\n".join(all_text) if all_text else None

    except Exception as e:
        print(f"PDF OCR failed: {e}")
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                temp_ocr = f.name
            subprocess.run(
                ["ocrmypdf", "--force-ocr", str(filepath), temp_ocr],
                capture_output=True,
                check=True,
            )
            result = subprocess.run(["pdftotext", temp_ocr, "-"], capture_output=True, text=True)
            Path(temp_ocr).unlink(missing_ok=True)
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
