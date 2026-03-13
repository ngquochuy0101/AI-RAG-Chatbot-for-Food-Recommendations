<?php
/**
 * Account Management API
 * Handles: Password Reset, Profile Update, Change Password, Delete Account, Login History
 */

// Set timezone to match MySQL
date_default_timezone_set('Asia/Ho_Chi_Minh');

require_once 'config.php';

$conn = getDBConnection();

// Set MySQL timezone to match PHP
$conn->query("SET time_zone = '+07:00'");

// Get request data
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    $action = $input['action'] ?? '';
    
    switch ($action) {
        case 'forgotPassword':
            forgotPassword($conn, $input);
            break;
        case 'verifyResetCode':
            verifyResetCode($conn, $input);
            break;
        case 'resetPassword':
            resetPassword($conn, $input);
            break;
        case 'updateProfile':
            updateProfile($conn, $input);
            break;
        case 'changePassword':
            changePassword($conn, $input);
            break;
        case 'deleteAccount':
            deleteAccount($conn, $input);
            break;
        case 'logLogin':
            logLogin($conn, $input);
            break;
        default:
            echo json_encode(['success' => false, 'message' => 'Invalid action']);
    }
} elseif ($method === 'GET') {
    $action = $_GET['action'] ?? '';
    
    switch ($action) {
        case 'getProfile':
            getProfile($conn);
            break;
        case 'getLoginHistory':
            getLoginHistory($conn);
            break;
        case 'getStats':
            getStats($conn);
            break;
        default:
            echo json_encode(['success' => false, 'message' => 'Invalid action']);
    }
}

/**
 * Forgot Password - Send reset code to email
 */
function forgotPassword($conn, $data) {
    $email = $conn->real_escape_string(trim($data['email'] ?? ''));
    
    if (empty($email)) {
        echo json_encode(['success' => false, 'message' => 'Email không được để trống!']);
        return;
    }
    
    // Check if email exists
    $check_sql = "SELECT id, name FROM users WHERE email = '$email'";
    $result = $conn->query($check_sql);
    
    if ($result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Email không tồn tại trong hệ thống!']);
        return;
    }
    
    $user = $result->fetch_assoc();
    
    // Generate 6-digit reset code
    $resetCode = sprintf("%06d", mt_rand(0, 999999));
    $expiresAt = date('Y-m-d H:i:s', strtotime('+15 minutes')); // Code expires in 15 minutes
    
    // Delete old reset codes for this user
    $delete_sql = "DELETE FROM password_resets WHERE email = '$email'";
    $conn->query($delete_sql);
    
    // Save reset code to database
    $insert_sql = "INSERT INTO password_resets (email, code, expires_at, created_at) 
                   VALUES ('$email', '$resetCode', '$expiresAt', NOW())";
    
    if ($conn->query($insert_sql)) {
        // Only expose reset code when explicitly enabled for demo/testing.
        $allowResetCodeResponse = strtolower(getenv('EXPOSE_RESET_CODE') ?: 'false') === 'true';

        $response = [
            'success' => true,
            'message' => 'Mã xác nhận đã được tạo. Vui lòng kiểm tra email hoặc kênh gửi mã của hệ thống.'
        ];

        if ($allowResetCodeResponse) {
            $response['resetCode'] = $resetCode;
            $response['message'] = 'Mã xác nhận (chế độ demo): ' . $resetCode . ' (Có hiệu lực trong 15 phút)';
        }

        echo json_encode($response);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể tạo mã xác nhận!']);
    }
}

/**
 * Verify Reset Code
 */
function verifyResetCode($conn, $data) {
    $email = $conn->real_escape_string(trim($data['email'] ?? ''));
    $code = $conn->real_escape_string(trim($data['code'] ?? ''));
    
    if (empty($email) || empty($code)) {
        echo json_encode(['success' => false, 'message' => 'Email và mã xác nhận không được để trống!']);
        return;
    }
    
    // Check if code is valid and not expired
    $sql = "SELECT * FROM password_resets 
            WHERE email = '$email' 
            AND code = '$code' 
            AND expires_at > NOW() 
            AND used = 0
            ORDER BY created_at DESC 
            LIMIT 1";
    
    $result = $conn->query($sql);
    
    if ($result->num_rows > 0) {
        echo json_encode(['success' => true, 'message' => 'Mã xác nhận hợp lệ!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Mã xác nhận không hợp lệ hoặc đã hết hạn!']);
    }
}

/**
 * Reset Password
 */
function resetPassword($conn, $data) {
    $email = $conn->real_escape_string(trim($data['email'] ?? ''));
    $code = $conn->real_escape_string(trim($data['code'] ?? ''));
    $newPassword = trim($data['newPassword'] ?? '');
    
    if (empty($email) || empty($code) || empty($newPassword)) {
        echo json_encode(['success' => false, 'message' => 'Vui lòng điền đầy đủ thông tin!']);
        return;
    }
    
    if (strlen($newPassword) < 6) {
        echo json_encode(['success' => false, 'message' => 'Mật khẩu phải có ít nhất 6 ký tự!']);
        return;
    }
    
    // Verify code
    $verify_sql = "SELECT * FROM password_resets 
                   WHERE email = '$email' 
                   AND code = '$code' 
                   AND expires_at > NOW() 
                   AND used = 0
                   ORDER BY created_at DESC 
                   LIMIT 1";
    $result = $conn->query($verify_sql);

    if ($result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Mã xác nhận không hợp lệ hoặc đã hết hạn!']);
        return;
    }
    
    // Hash new password
    $hashedPassword = password_hash($newPassword, PASSWORD_BCRYPT);
    
    // Update password
    $update_sql = "UPDATE users SET password = '$hashedPassword' WHERE email = '$email'";
    if ($conn->query($update_sql)) {
        // Mark code as used
        $mark_used_sql = "UPDATE password_resets SET used = 1 WHERE email = '$email' AND code = '$code'";
        $conn->query($mark_used_sql);
        
        echo json_encode(['success' => true, 'message' => 'Mật khẩu đã được đặt lại thành công!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể đặt lại mật khẩu!']);
    }
}

/**
 * Update Profile
 */
function updateProfile($conn, $data) {
    $userId = intval($data['userId'] ?? 0);
    $name = $conn->real_escape_string(trim($data['name'] ?? ''));
    
    if (!$userId || empty($name)) {
        echo json_encode(['success' => false, 'message' => 'Thông tin không hợp lệ!']);
        return;
    }
    
    $update_sql = "UPDATE users SET name = '$name' WHERE id = $userId";
    
    if ($conn->query($update_sql)) {
        echo json_encode([
            'success' => true,
            'message' => 'Cập nhật thông tin thành công!',
            'user' => ['id' => $userId, 'name' => $name]
        ]);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể cập nhật thông tin!']);
    }
}

/**
 * Change Password
 */
function changePassword($conn, $data) {
    $userId = intval($data['userId'] ?? 0);
    $currentPassword = trim($data['currentPassword'] ?? '');
    $newPassword = trim($data['newPassword'] ?? '');
    
    if (!$userId || empty($currentPassword) || empty($newPassword)) {
        echo json_encode(['success' => false, 'message' => 'Vui lòng điền đầy đủ thông tin!']);
        return;
    }
    
    if (strlen($newPassword) < 6) {
        echo json_encode(['success' => false, 'message' => 'Mật khẩu mới phải có ít nhất 6 ký tự!']);
        return;
    }
    
    // Get current password hash
    $check_sql = "SELECT password FROM users WHERE id = $userId";
    $result = $conn->query($check_sql);
    
    if ($result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Người dùng không tồn tại!']);
        return;
    }
    
    $user = $result->fetch_assoc();
    
    // Verify current password
    if (!password_verify($currentPassword, $user['password'])) {
        echo json_encode(['success' => false, 'message' => 'Mật khẩu hiện tại không đúng!']);
        return;
    }
    
    // Hash new password
    $hashedPassword = password_hash($newPassword, PASSWORD_BCRYPT);
    
    // Update password
    $update_sql = "UPDATE users SET password = '$hashedPassword' WHERE id = $userId";
    
    if ($conn->query($update_sql)) {
        echo json_encode(['success' => true, 'message' => 'Đổi mật khẩu thành công!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể đổi mật khẩu!']);
    }
}

/**
 * Delete Account
 */
function deleteAccount($conn, $data) {
    $userId = intval($data['userId'] ?? 0);
    $password = trim($data['password'] ?? '');
    
    if (!$userId || empty($password)) {
        echo json_encode(['success' => false, 'message' => 'Thông tin không hợp lệ!']);
        return;
    }
    
    // Get user password
    $check_sql = "SELECT password FROM users WHERE id = $userId";
    $result = $conn->query($check_sql);
    
    if ($result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Người dùng không tồn tại!']);
        return;
    }
    
    $user = $result->fetch_assoc();
    
    // Verify password
    if (!password_verify($password, $user['password'])) {
        echo json_encode(['success' => false, 'message' => 'Mật khẩu không đúng!']);
        return;
    }
    
    // Delete user (CASCADE will delete chats, messages, reports)
    $delete_sql = "DELETE FROM users WHERE id = $userId";
    
    if ($conn->query($delete_sql)) {
        echo json_encode(['success' => true, 'message' => 'Tài khoản đã được xóa thành công!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể xóa tài khoản!']);
    }
}

/**
 * Get Profile
 */
function getProfile($conn) {
    $userId = intval($_GET['userId'] ?? 0);
    
    if (!$userId) {
        echo json_encode(['success' => false, 'message' => 'User ID required']);
        return;
    }
    
    $sql = "SELECT id, name, email, created_at, last_login FROM users WHERE id = $userId";
    $result = $conn->query($sql);
    
    if ($result->num_rows > 0) {
        $user = $result->fetch_assoc();
        echo json_encode(['success' => true, 'user' => $user]);
    } else {
        echo json_encode(['success' => false, 'message' => 'Người dùng không tồn tại!']);
    }
}

/**
 * Get Login History
 */
function getLoginHistory($conn) {
    $userId = intval($_GET['userId'] ?? 0);
    
    if (!$userId) {
        echo json_encode(['success' => false, 'message' => 'User ID required']);
        return;
    }
    
    $sql = "SELECT * FROM login_history 
            WHERE user_id = $userId 
            ORDER BY login_at DESC 
            LIMIT 10";
    
    $result = $conn->query($sql);
    
    $history = [];
    while ($row = $result->fetch_assoc()) {
        $history[] = $row;
    }
    
    echo json_encode(['success' => true, 'history' => $history]);
}

/**
 * Log Login
 */
function logLogin($conn, $data) {
    $userId = intval($data['userId'] ?? 0);
    $ipAddress = $_SERVER['REMOTE_ADDR'];
    $userAgent = $conn->real_escape_string($_SERVER['HTTP_USER_AGENT'] ?? 'Unknown');
    
    if (!$userId) {
        echo json_encode(['success' => false, 'message' => 'User ID required']);
        return;
    }
    
    $sql = "INSERT INTO login_history (user_id, ip_address, user_agent, login_at) 
            VALUES ($userId, '$ipAddress', '$userAgent', NOW())";
    
    if ($conn->query($sql)) {
        // Update last_login in users table
        $update_sql = "UPDATE users SET last_login = NOW() WHERE id = $userId";
        $conn->query($update_sql);
        
        echo json_encode(['success' => true]);
    } else {
        echo json_encode(['success' => false, 'message' => 'Failed to log login']);
    }
}

/**
 * Get User Statistics
 */
function getStats($conn) {
    $userId = intval($_GET['userId'] ?? 0);
    
    if (!$userId) {
        echo json_encode(['success' => false, 'message' => 'User ID required']);
        return;
    }
    
    // Get total chats
    $chats_sql = "SELECT COUNT(*) as total FROM chats WHERE user_id = $userId";
    $chats_result = $conn->query($chats_sql);
    $totalChats = $chats_result->fetch_assoc()['total'];
    
    // Get total messages
    $messages_sql = "SELECT COUNT(m.id) as total 
                     FROM messages m 
                     JOIN chats c ON m.chat_id = c.id 
                     WHERE c.user_id = $userId";
    $messages_result = $conn->query($messages_sql);
    $totalMessages = $messages_result->fetch_assoc()['total'];
    
    echo json_encode([
        'success' => true,
        'stats' => [
            'totalChats' => $totalChats,
            'totalMessages' => $totalMessages
        ]
    ]);
}

/**
 * Send Reset Email (Mock function)
 * In production: Use PHPMailer or similar
 */
function sendResetEmail($email, $name, $code) {
    // Mock email sending
    // In production, use PHPMailer:
    /*
    require 'PHPMailer/PHPMailer.php';
    require 'PHPMailer/SMTP.php';
    
    $mail = new PHPMailer\PHPMailer\PHPMailer();
    $mail->isSMTP();
    $mail->Host = 'smtp.gmail.com';
    $mail->SMTPAuth = true;
    $mail->Username = 'your-email@gmail.com';
    $mail->Password = 'your-app-password';
    $mail->SMTPSecure = PHPMailer\PHPMailer\PHPMailer::ENCRYPTION_STARTTLS;
    $mail->Port = 587;
    
    $mail->setFrom('noreply@chatbot.com', 'Chatbot');
    $mail->addAddress($email, $name);
    
    $mail->Subject = 'Mã đặt lại mật khẩu';
    $mail->Body = "Xin chào $name,\n\nMã xác nhận của bạn là: $code\n\nMã có hiệu lực trong 15 phút.";
    
    return $mail->send();
    */
    
    // For demo: return false to show code in response
    return false;
}

$conn->close();
?>
