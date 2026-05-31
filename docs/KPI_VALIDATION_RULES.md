# KPI Validation Rules cho TeamsWork

Tài liệu này chuẩn hóa công thức KPI hiện tại và các test case bắt buộc. Khi tài liệu và code khác nhau, lấy `app/kpi.py` làm nguồn sự thật hiện tại và cập nhật lại tài liệu sau khi có human approval.

## 1. Phạm vi tính KPI

KPI tháng nhận tham số `month` dạng `YYYY-MM`.

Một task được tính vào tháng nếu:

- `deadline` parse được thành datetime.
- `deadline` nằm trong khoảng từ ngày đầu tháng `00:00:00 UTC` đến ngày cuối tháng `23:59:59 UTC`.

Task có deadline ngoài tháng không được tính vào KPI tháng đó.

## 2. Công thức KPI hiện tại

Với mỗi task thuộc tháng KPI:

- Hoàn thành đúng hạn: `score += 10 * difficulty_multiplier`.
- Hoàn thành trễ hạn: `score += 5 * difficulty_multiplier`.
- Chưa hoàn thành và deadline thuộc tháng: `score -= 5 * difficulty_multiplier`.

Điểm cuối được làm tròn 2 chữ số thập phân.

Phase 3 Slice 1 note: these defaults are represented in code as `DEFAULT_KPI_POLICY` in `app/kpi.py`. This is a compatibility policy, not admin-editable configuration.

## 3. Difficulty Multiplier

Multiplier hiện tại:

| Difficulty | Multiplier |
|---|---:|
| `easy` | `1.0` |
| `medium` | `1.5` |
| `hard` | `2.0` |

Nếu difficulty không hợp lệ ở tầng tính toán, mặc định fallback là `1.0`. Ở tầng API/schema, dữ liệu task nên bị reject nếu difficulty không thuộc `easy|medium|hard`.

## 4. Case Đúng Hạn

Điều kiện:

- `status == "done"`.
- `completed_at` tồn tại.
- `completed_at <= deadline`.

Ví dụ:

- Task `easy`, deadline `2026-04-10`, completed `2026-04-09`.
- Điểm: `10 * 1.0 = 10`.
- Counter `done_on_time += 1`.

## 5. Case Trễ Hạn

Điều kiện:

- `status == "done"`.
- `completed_at` tồn tại.
- `completed_at > deadline`.

Ví dụ:

- Task `hard`, deadline `2026-04-10`, completed `2026-04-12`.
- Điểm: `5 * 2.0 = 10`.
- Counter `done_late += 1`.

## 6. Case Quá Hạn Chưa Xong

Điều kiện:

- `status != "done"`.
- `deadline` thuộc tháng KPI.

Ví dụ:

- Task `medium`, status `todo`, deadline `2026-04-15`.
- Điểm: `-5 * 1.5 = -7.5`.
- Counter `overdue_unfinished += 1`.

Lưu ý: hàm KPI tháng đang coi task chưa done có deadline trong tháng là quá hạn/chưa xong khi tổng kết tháng.

## 7. Manual Adjustment

Manual adjustment được cộng/trừ trực tiếp vào điểm cuối:

```text
final_score = calculated_score + sum(adjustment.points)
```

Quy tắc:

- Chỉ `admin`, `manager`, `hr` được tạo adjustment.
- Adjustment phải có `user_id`, `month`, `points`, `reason`.
- `reason` phải đủ rõ để review.
- Tạo adjustment phải ghi audit log.
- Adjustment không được dùng để âm thầm thay đổi công thức KPI.

Phase 3 update: manager-created adjustments start as `pending` and do not affect score until HR/admin approval. HR/admin-created adjustments are auto-approved and still require reason/audit evidence. Approved adjustments are materialized into `kpi_transactions`; pending or rejected adjustments are excluded from KPI score.

## 7.1 KPI Transaction Ledger

KPI monthly API/report paths rebuild active ledger rows for the requested month before aggregating score.

- Task events use a unique event key per task/month/outcome and remain idempotent across rebuilds.
- Reopened, deleted, or changed task outcomes reverse stale ledger rows instead of deleting evidence.
- KPI report rows aggregate only active ledger rows.

## 7.2 KPI Targets

KPI targets store user/month `target_score` and are compared with ledger score.

- `progress_percent = score / target_score * 100`.
- `gap = max(target_score - score, 0)`.
- KPI target warnings are notifications and must deduplicate within the daily run window.

## 8. Test Case Bắt Buộc

Tối thiểu phải có các case sau:

- Một task đúng hạn `easy`: cộng `10`.
- Một task trễ hạn `hard`: cộng `10`.
- Một task chưa xong `medium`: trừ `7.5`.
- Tổng ví dụ trên cho cùng user: `12.5`.
- Task ngoài tháng không ảnh hưởng tháng đang tính.
- Adjustment dương làm tăng điểm.
- Adjustment âm làm giảm điểm.
- User chỉ có adjustment nhưng không có task vẫn xuất hiện trong report.

## 9. Edge Cases

- `deadline` không parse được: cần reject ở tầng API hoặc xử lý lỗi rõ ràng.
- `completed_at` rỗng với `status == "done"`: không được tính là done đúng/trễ.
- Datetime không có timezone: code hiện tại coi là UTC.
- Deadline đúng ranh giới đầu/cuối tháng phải được tính trong tháng.
- Nhiều adjustment cùng user/tháng được cộng dồn.
- Score có thể âm nếu task quá hạn nhiều hoặc adjustment âm.

## 10. Điều Kiện Cần Human Approval Khi Đổi Công Thức

Cần approval rõ từ người phụ trách dự án nếu thay đổi:

- Điểm base `10`, `5`, `-5`.
- Difficulty multiplier.
- Cách xác định đúng hạn/trễ hạn/quá hạn.
- Cách tính task ngoài tháng hoặc task đang làm.
- Cách áp dụng manual adjustment.
- Cách hiển thị/xếp hạng KPI trong report/dashboard.

Khi được duyệt đổi công thức, phải cập nhật đồng thời:

- `app/kpi.py`.
- `tests/test_kpi.py` và test API/report liên quan.
- `docs/KPI_VALIDATION_RULES.md`.
- `docs/QUALITY_GATE.md` nếu checklist thay đổi.
