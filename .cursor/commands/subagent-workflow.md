---
description: Chạy workflow Subagent Manager — intake → WBS → delegate → consolidate → verify → (tuỳ chọn) persist plan. Gọi một lệnh để điều phối toàn bộ chuỗi.
argument-hint: "[mục tiêu ngắn] | [file/module cần đụng] | [DoD hoặc tiêu chí xong]"
---

# Subagent Workflow — Một lệnh gọi chuỗi workflow

Bạn đang chạy **Subagent Manager workflow**. Thực hiện đúng 7 bước orchestration và tuân thủ output format cứng.

## Nhiệm vụ

1. **Đọc và áp dụng** toàn bộ protocol trong **`.cursor/agents/subagent-manager.md`** (Mission, Delegation Map, Orchestration Procedure 7 bước, Conflict resolution, Output format A–H, DoD, Persistence).
2. **Input từ user** (nếu có trong tin nhắn): dùng làm mục tiêu/DoD/constraint. Nếu thiếu: hỏi ngắn gọn theo thứ tự ảnh hưởng lớn nhất (tối đa 5 câu).
3. **Chạy tuần tự**: Intake & framing → WBS → Delegation briefs → Consolidation → Decision & plan → Verification gate → (tuỳ chọn) Persist plan vào `.cursor/plans/<short-topic>.md`.
4. **Output** phải theo đúng cấu trúc A–H trong subagent-manager (Situation, Delegation Plan, Results Digest, Integrated Decisions, Action Plan, Verification Checklist, Risk/Rollback, Open questions).

## Ràng buộc

- Không bỏ bước; không báo "xong" nếu chưa có checklist verify cụ thể (lệnh + tiêu chí pass).
- Khi có diff/code: bắt buộc gọi (hoặc mô phỏng brief cho) Code Reviewer và Verifier theo Delegation Map.
- Nếu task kéo dài nhiều phiên: tạo hoặc cập nhật `.cursor/plans/<short-topic>.md` với WBS, quyết định, action plan, verification checklist, risk/rollback.

## Bắt đầu

Coi nội dung tin nhắn của user (nếu có) là **mục tiêu / DoD / phạm vi**. Bắt đầu bằng **Bước 1 — Intake & framing**, rồi lần lượt thực hiện đến Bước 7. Xuất báo cáo điều phối theo đúng format A–H.
