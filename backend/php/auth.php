<?php
require_once 'config.php';

$conn = getDBConnection();

// Get request data
$method = $_SERVER['REQUEST_METHOD'];
$input = json_decode(file_get_contents('php://input'), true);

if ($method === 'POST') {
    $action = $input['action'] ?? '';
    
    if ($action === 'register') {
        register($conn, $input);
    } elseif ($action === 'login') {
        login($conn, $input);
    } else {
        echo json_encode(['success' => false, 'message' => 'Invalid action']);
    }
}

function register($conn, $data) {
    $name = $conn->real_escape_string(trim($data['name'] ?? ''));
    $email = $conn->real_escape_string(trim($data['email'] ?? ''));
    $password = $data['password'] ?? '';
    
    // Validate input
    if (empty($name) || empty($email) || empty($password)) {
        echo json_encode(['success' => false, 'message' => 'Vui lòng điền đầy đủ thông tin!']);
        return;
    }
    
    // Check if email exists
    $check_sql = "SELECT id FROM users WHERE email = '$email'";
    $check_result = $conn->query($check_sql);
    
    if ($check_result->num_rows > 0) {
        echo json_encode(['success' => false, 'message' => 'Email đã tồn tại!']);
        return;
    }
    
    // Hash password
    $hashed_password = password_hash($password, PASSWORD_DEFAULT);
    
    // Insert user
    $sql = "INSERT INTO users (name, email, password, created_at) 
            VALUES ('$name', '$email', '$hashed_password', NOW())";
    
    if ($conn->query($sql)) {
        echo json_encode([
            'success' => true,
            'message' => 'Đăng ký thành công!'
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'message' => 'Đăng ký thất bại: ' . $conn->error
        ]);
    }
}

function login($conn, $data) {
    $email = $conn->real_escape_string(trim($data['email'] ?? ''));
    $password = $data['password'] ?? '';
    
    // Validate input
    if (empty($email) || empty($password)) {
        echo json_encode(['success' => false, 'message' => 'Vui lòng điền đầy đủ thông tin!']);
        return;
    }
    
    // Find user
    $sql = "SELECT * FROM users WHERE email = '$email'";
    $result = $conn->query($sql);
    
    if ($result->num_rows === 1) {
        $user = $result->fetch_assoc();
        
        // Verify password
        if (password_verify($password, $user['password'])) {
            // Update last login
            $user_id = $user['id'];
            $update_sql = "UPDATE users SET last_login = NOW() WHERE id = $user_id";
            $conn->query($update_sql);
            
            // Generate token
            $token = base64_encode($user['id'] . ':' . time() . ':' . bin2hex(random_bytes(16)));
            
            echo json_encode([
                'success' => true,
                'token' => $token,
                'user' => [
                    'id' => $user['id'],
                    'name' => $user['name'],
                    'email' => $user['email']
                ]
            ]);
        } else {
            echo json_encode(['success' => false, 'message' => 'Mật khẩu không đúng!']);
        }
    } else {
        echo json_encode(['success' => false, 'message' => 'Email không tồn tại!']);
    }
}

$conn->close();
?>
