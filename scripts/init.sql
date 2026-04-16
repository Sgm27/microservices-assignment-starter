-- ==============================================
-- Cinema Ticket Booking — DB initialization
-- Creates one database per service.
-- Auto-loaded by mysql-db on first start.
-- ==============================================

CREATE DATABASE IF NOT EXISTS auth_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS user_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS movie_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS voucher_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS booking_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS payment_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS notification_db
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Root user is granted all privileges by default in single-instance MySQL.
FLUSH PRIVILEGES;
