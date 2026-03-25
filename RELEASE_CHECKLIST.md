# Release Checklist (Production)

## 1) Quality Gates
- [x] `python -m flake8 .` pass
- [x] `python -m mypy .` pass
- [x] `python -m pytest -q` pass
- [x] `python -m pip_audit` pass

## 2) Versioning and Artifact
- [ ] Bump version theo quy ước dự án
- [ ] Tạo release note ngắn: thay đổi chính, risk, known limitations
- [ ] Đóng gói artifact chạy production

## 3) Deploy and Verification
- [ ] Deploy lên môi trường production theo runbook
- [ ] Smoke test các luồng chính sau deploy
- [ ] Xác nhận logging/monitoring hoạt động bình thường

## 4) Rollback Readiness
- [ ] Xác nhận rollback command/procedure khả dụng
- [ ] Thực hiện rollback drill ngắn (hoặc dry-run)
- [ ] Ghi nhận thời gian khôi phục mục tiêu (RTO) thực tế

## 5) Sign-off
- [ ] Owner kỹ thuật sign-off
- [ ] Product/Business sign-off (nếu cần)
- [ ] Chốt trạng thái production-ready

## Current status
- Quality gate đã pass theo phiên verify hiện tại.
- Còn lại các bước vận hành release: version/artifact, deploy/smoke test, rollback drill, sign-off.
