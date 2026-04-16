# System Architecture

> Tài liệu này được hoàn thành **sau** [Analysis and Design](analysis-and-design.md).
> Dựa trên Service Candidates và Non-Functional Requirements đã xác định, chọn các architecture pattern phù hợp và thiết kế deployment architecture.

**References:**

1. *Service-Oriented Architecture: Analysis and Design for Services and Microservices* — Thomas Erl (2nd Edition)
2. *Microservices Patterns: With Examples in Java* — Chris Richardson
3. *Bài tập — Phát triển phần mềm hướng dịch vụ* — Hung Dang (available in Vietnamese)

---

## 1. Pattern Selection

| Pattern | Selected? | Business/Technical Justification |
|---------|-----------|----------------------------------|
| API Gateway | Yes | Cung cấp single entry point cho toàn hệ thống, tập trung xử lý xác thực JWT, routing đến các service và giảm độ phức tạp cho client web. |
| Database per Service | Yes | Mỗi service sở hữu schema riêng trên MySQL, đảm bảo tính độc lập dữ liệu và khả năng triển khai/độc lập tiến hoá giữa các service. |
| Saga — Orchestration (Temporal) | Yes | Luồng đặt vé trải qua nhiều bước trên nhiều service (reserve seats → validate voucher → create payment → confirm/release) với yêu cầu consistency và compensation. Dùng Temporal workflow làm orchestrator để quản lý state, retry, timeout (5 phút) và compensating transaction một cách tường minh thay vì choreography rải rác. |
| Workflow as Code (Temporal) | Yes | Business logic của luồng booking được mô hình hoá thành code Python (`BookingWorkflow`) chạy trên Temporal, cho phép versioning, test, replay và quan sát được toàn bộ state transition. |
| Circuit Breaker | Yes | Ngăn chặn lỗi lan rộng khi các service phụ thuộc (payment, movie, voucher) không phản hồi; Booking workflow có timeout rõ ràng cho mỗi activity. |

> Reference: *Microservices Patterns* — Chris Richardson, chapters on decomposition, data management, and communication patterns.

---

## 2. System Components

| Component | Responsibility | Tech Stack | Port |
|-----------|----------------|-----------|------|
| **Frontend** | Giao diện người dùng — đăng nhập, xem phim, chọn suất chiếu, chọn ghế, thanh toán | React 18, TypeScript, Vite, React Router, Axios | 5173 |
| **Gateway** | Single entry point — xác thực JWT, routing đến các service | Python, FastAPI, Uvicorn | 5000 |
| **Auth Service** | Register, login, cấp và verify JWT | Python, FastAPI, SQLAlchemy, MySQL | 5001 |
| **User Service** | Quản lý thông tin user (profile) | Python, FastAPI, SQLAlchemy, MySQL | 5002 |
| **Movie Service** | Quản lý phim, suất chiếu, ghế; reserve/confirm/release seats | Python, FastAPI, SQLAlchemy, MySQL | 5003 |
| **Voucher Service** | Quản lý mã giảm giá: list / create / validate / redeem | Python, FastAPI, SQLAlchemy, MySQL | 5004 |
| **Booking Service** | Saga orchestrator — Temporal workflow cho luồng đặt vé, compensation khi fail/timeout | Python, FastAPI, Temporal SDK, MySQL | 5005 |
| **Payment Service** | Tạo mock/VNPay payment URL, nhận kết quả thanh toán (mock confirm hoặc VNPay IPN) | Python, FastAPI, SQLAlchemy, MySQL | 5006 |
| **Notification Service** | Gửi email thông báo booking (mock trong dev) | Python, FastAPI, SQLAlchemy, MySQL | 5007 |
| **MySQL** | Cơ sở dữ liệu chung — mỗi service sở hữu schema riêng | MySQL 8.0 | 3307 |
| **Temporal** | Workflow engine cho Saga orchestration; dùng PostgreSQL làm persistent store | Temporal 1.24.2, PostgreSQL 15 | 7233 |

---

## 3. Communication

### Inter-service Communication Matrix

| From \ To | Gateway | Auth | User | Movie | Voucher | Booking | Payment | Notification | VNPay (External) |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Frontend** | HTTP/REST | - | - | - | - | - | - | - | - |
| **Gateway** | - | HTTP/REST *(verify)* | HTTP/REST *(forward)* | HTTP/REST *(forward)* | HTTP/REST *(forward)* | HTTP/REST *(forward)* | HTTP/REST *(forward)* | HTTP/REST *(forward)* | - |
| **Booking (Workflow)** | - | - | - | HTTP (POST) *(/seats/reserve, /seats/confirm, /seats/release)* | HTTP (POST) *(/vouchers/validate, /vouchers/redeem)* | - | HTTP (POST/GET) *(/payments/create, /payments/{id} poll)* | HTTP (POST) *(/notifications/send)* | - |
| **Payment** | - | - | - | - | - | - | - | - | HTTP/Redirect *(VNPay sandbox)* |
| **VNPay** | - | - | - | - | - | - | Webhook (GET) *(/payments/vnpay-return)* | - | - |

> Booking không gọi trực tiếp activities qua message queue — toàn bộ orchestration được Temporal workflow điều phối, activities là HTTP client call có retry/timeout do Temporal quản lý.

---

## 4. Architecture Diagram

> Đặt diagram trong `docs/asset/` và reference tại đây.
>
> ![Architecture Diagram](asset/architecture-diagram.png)
>
> *(Placeholder — nhóm tự tạo diagram và thay ảnh.)*

---

## 5. Deployment

- All services containerized với Docker
- Orchestrated qua Docker Compose (xem `docker-compose.yaml` ở root)
- MySQL 8.0 (port 3307) và Temporal 1.24.2 (port 7233, backend PostgreSQL 15) chạy cùng compose stack
- Single command: `docker compose up --build`
- Environment config: copy `.env.example` → `.env` trước khi run
