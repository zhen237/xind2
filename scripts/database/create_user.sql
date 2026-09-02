CREATE USER 'appuser'@'%' IDENTIFIED WITH mysql_native_password BY 'apppass123';
GRANT ALL PRIVILEGES ON comm_platform.* TO 'appuser'@'%';
FLUSH PRIVILEGES;