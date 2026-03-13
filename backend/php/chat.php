<?php
require_once 'config.php';

$conn = getDBConnection();

// Get request data
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    $action = $input['action'] ?? '';
    
    switch ($action) {
        case 'sendMessage':
            sendMessage($conn, $input);
            break;
        case 'reportMessage':
            reportMessage($conn, $input);
            break;
        case 'updateChatTitle':
            updateChatTitle($conn, $input);
            break;
        case 'deleteChat':
            deleteChat($conn, $input);
            break;
        case 'pinChat':
            pinChat($conn, $input);
            break;
        default:
            echo json_encode(['success' => false, 'message' => 'Invalid action']);
    }
} elseif ($method === 'GET') {
    $action = $_GET['action'] ?? '';
    
    switch ($action) {
        case 'getHistory':
            getHistory($conn);
            break;
        case 'getMessages':
            getMessages($conn);
            break;
        default:
            echo json_encode(['success' => false, 'message' => 'Invalid action']);
    }
}

function sendMessage($conn, $data) {
    $message = $conn->real_escape_string(trim($data['message'] ?? ''));
    $userId = intval($data['userId'] ?? 0);
    $chatId = intval($data['chatId'] ?? 0);
    
    // Validate
    if (empty($message)) {
        echo json_encode(['success' => false, 'message' => 'Tin nhắn không được để trống!']);
        return;
    }
    
    // Create new chat if needed
    if (!$chatId && $userId) {
        $title = $conn->real_escape_string(substr($message, 0, 50));
        $create_chat_sql = "INSERT INTO chats (user_id, title, created_at, updated_at) 
                           VALUES ($userId, '$title', NOW(), NOW())";
        
        if ($conn->query($create_chat_sql)) {
            $chatId = $conn->insert_id;
        }
    }
    
    // Save user message
    if ($chatId) {
        $save_user_sql = "INSERT INTO messages (chat_id, type, message, created_at) 
                         VALUES ($chatId, 'user', '$message', NOW())";
        $conn->query($save_user_sql);
        
        // Update chat timestamp
        $update_chat_sql = "UPDATE chats SET updated_at = NOW() WHERE id = $chatId";
        $conn->query($update_chat_sql);
    }
    
    // ========== GỌI PYTHON AI API ==========
    // Thay vì trả về "hello", gọi Python FastAPI
    $aiResponse = callPythonAI($message, $userId, $chatId);
    $response = $aiResponse['response'];
    $responseHtml = $aiResponse['response_html'];
    
    // Save AI response (markdown text)
    if ($chatId) {
        $ai_message = $conn->real_escape_string($response);
        $ai_message_html = $conn->real_escape_string($responseHtml);
        
        $save_ai_sql = "INSERT INTO messages (chat_id, type, message, response_html, created_at) 
                       VALUES ($chatId, 'assistant', '$ai_message', '$ai_message_html', NOW())";
        $conn->query($save_ai_sql);
    }
    
    echo json_encode([
        'success' => true,
        'response' => $response,
        'response_html' => $responseHtml,
        'chatId' => $chatId
    ]);
}

/**
 * Gọi Python FastAPI để lấy AI response
 * @param string $message - Tin nhắn từ user
 * @param int $userId - User ID
 * @param int $chatId - Chat ID
 * @return array - ['response' => markdown_text, 'response_html' => html]
 */
function callPythonAI($message, $userId, $chatId) {
    // URL của Python FastAPI server (use ENV or default to localhost:8001)
    $pythonApiBase = getenv('PYTHON_API_URL') ?: 'http://localhost:8001';
    // Ensure no double slash if base ends with /
    $pythonApiUrl = rtrim($pythonApiBase, '/') . '/chat';
    
    // Data gửi đi
    $postData = json_encode([
        'message' => $message,
        'user_id' => $userId,
        'chat_id' => $chatId,
        'context' => null
    ]);
    
    // Khởi tạo cURL
    $ch = curl_init($pythonApiUrl);
    
    // Cấu hình cURL
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Content-Length: ' . strlen($postData)
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 200); 
    
    // Thực thi request
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    // Kiểm tra lỗi
    if ($error) {
        // Log error (optional)
        error_log("Python AI Error: " . $error);
        return [
            'response' => "Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau!",
            'response_html' => '<p>Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau!</p>'
        ];
    }
    
    if ($httpCode !== 200) {
        error_log("Python AI HTTP Error: " . $httpCode);
        return [
            'response' => "Xin lỗi, không thể kết nối đến AI. Vui lòng thử lại!",
            'response_html' => '<p>Xin lỗi, không thể kết nối đến AI. Vui lòng thử lại!</p>'
        ];
    }
    
    // Parse JSON response
    $result = json_decode($response, true);
    
    if ($result && isset($result['response']) && isset($result['response_html'])) {
        return [
            'response' => $result['response'],
            'response_html' => $result['response_html']
        ];
    }
    
    // Fallback response
    return [
        'response' => "Xin lỗi, tôi không hiểu câu hỏi của bạn. Bạn có thể hỏi lại được không?",
        'response_html' => '<p>Xin lỗi, tôi không hiểu câu hỏi của bạn. Bạn có thể hỏi lại được không?</p>'
    ];
}

function getHistory($conn) {
    $userId = intval($_GET['userId'] ?? 0);
    
    if (!$userId) {
        echo json_encode(['success' => false, 'message' => 'User ID required']);
        return;
    }
    
    // Sort: pinned chats first, then by updated_at DESC
    $sql = "SELECT * FROM chats WHERE user_id = $userId ORDER BY is_pinned DESC, updated_at DESC";
    $result = $conn->query($sql);
    
    $history = [];
    while ($row = $result->fetch_assoc()) {
        $history[] = $row;
    }
    
    echo json_encode([
        'success' => true,
        'history' => $history
    ]);
}

function getMessages($conn) {
    $chatId = intval($_GET['chatId'] ?? 0);
    
    if (!$chatId) {
        echo json_encode(['success' => false, 'message' => 'Chat ID required']);
        return;
    }
    
    $sql = "SELECT * FROM messages WHERE chat_id = $chatId ORDER BY created_at ASC";
    $result = $conn->query($sql);
    
    $messages = [];
    while ($row = $result->fetch_assoc()) {
        // Giữ nguyên response_html từ database (nếu có)
        $messages[] = $row;
    }
    
    echo json_encode([
        'success' => true,
        'messages' => $messages
    ]);
}

function reportMessage($conn, $data) {
    $message = $conn->real_escape_string(trim($data['message'] ?? ''));
    $userId = intval($data['userId'] ?? 0);
    $chatId = intval($data['chatId'] ?? 0);
    $reason = $conn->real_escape_string(trim($data['reason'] ?? 'other'));
    $reasonText = $conn->real_escape_string(trim($data['reasonText'] ?? 'Lý do khác'));
    $details = $conn->real_escape_string(trim($data['details'] ?? ''));
    
    // Allow guest reports (userId = 0) and empty messages (general reports)
    
    // Check if already reported by this user (only for logged in users with same message)
    if ($userId > 0 && !empty($message)) {
        $check_sql = "SELECT id FROM reports 
                      WHERE user_id = $userId 
                      AND message = '$message' 
                      AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)";
        $check_result = $conn->query($check_sql);
        
        if ($check_result->num_rows > 0) {
            echo json_encode(['success' => false, 'message' => 'Bạn đã báo cáo tin nhắn này gần đây!']);
            return;
        }
    }
    
    // Handle NULL chatId properly
    if ($chatId > 0) {
        $sql = "INSERT INTO reports (user_id, chat_id, message, reason, reason_text, details, status, created_at) 
                VALUES ($userId, $chatId, '$message', '$reason', '$reasonText', '$details', 'pending', NOW())";
    } else {
        $sql = "INSERT INTO reports (user_id, chat_id, message, reason, reason_text, details, status, created_at) 
                VALUES ($userId, NULL, '$message', '$reason', '$reasonText', '$details', 'pending', NOW())";
    }
    
    if ($conn->query($sql)) {
        echo json_encode(['success' => true, 'message' => 'Báo cáo đã được gửi thành công!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể gửi báo cáo!']);
    }
}

function updateChatTitle($conn, $data) {
    $chatId = intval($data['chatId'] ?? 0);
    $userId = intval($data['userId'] ?? 0);
    $title = $conn->real_escape_string(trim($data['title'] ?? ''));
    
    // Validate
    if (!$chatId || !$userId) {
        echo json_encode(['success' => false, 'message' => 'Chat ID and User ID required']);
        return;
    }
    
    if (empty($title)) {
        echo json_encode(['success' => false, 'message' => 'Tiêu đề không được để trống!']);
        return;
    }
    
    if (strlen($title) > 255) {
        echo json_encode(['success' => false, 'message' => 'Tiêu đề không được quá 255 ký tự!']);
        return;
    }
    
    // Verify ownership
    $verify_sql = "SELECT id FROM chats WHERE id = $chatId AND user_id = $userId";
    $verify_result = $conn->query($verify_sql);
    
    if ($verify_result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Không tìm thấy cuộc trò chuyện hoặc bạn không có quyền chỉnh sửa!']);
        return;
    }
    
    // Update title
    $update_sql = "UPDATE chats SET title = '$title' WHERE id = $chatId AND user_id = $userId";
    
    if ($conn->query($update_sql)) {
        echo json_encode(['success' => true, 'message' => 'Đã cập nhật tiêu đề!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể cập nhật tiêu đề!']);
    }
}

function deleteChat($conn, $data) {
    $chatId = intval($data['chatId'] ?? 0);
    $userId = intval($data['userId'] ?? 0);
    
    if (!$chatId || !$userId) {
        echo json_encode(['success' => false, 'message' => 'Chat ID and User ID required']);
        return;
    }
    
    // Verify ownership before deleting
    $verify_sql = "SELECT id FROM chats WHERE id = $chatId AND user_id = $userId";
    $verify_result = $conn->query($verify_sql);
    
    if ($verify_result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Unauthorized or chat not found']);
        return;
    }
    
    // Delete chat (CASCADE will delete messages automatically)
    $delete_sql = "DELETE FROM chats WHERE id = $chatId AND user_id = $userId";
    
    if ($conn->query($delete_sql)) {
        echo json_encode(['success' => true, 'message' => 'Đã xóa cuộc trò chuyện!']);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể xóa cuộc trò chuyện!']);
    }
}

function pinChat($conn, $data) {
    $chatId = intval($data['chatId'] ?? 0);
    $userId = intval($data['userId'] ?? 0);
    $isPinned = isset($data['isPinned']) ? ($data['isPinned'] ? 1 : 0) : 0;
    
    if (!$chatId || !$userId) {
        echo json_encode(['success' => false, 'message' => 'Chat ID and User ID required']);
        return;
    }
    
    // Verify ownership before pinning
    $verify_sql = "SELECT id FROM chats WHERE id = $chatId AND user_id = $userId";
    $verify_result = $conn->query($verify_sql);
    
    if ($verify_result->num_rows === 0) {
        echo json_encode(['success' => false, 'message' => 'Unauthorized or chat not found']);
        return;
    }
    
    // Update pin status
    $update_sql = "UPDATE chats SET is_pinned = $isPinned WHERE id = $chatId AND user_id = $userId";
    
    if ($conn->query($update_sql)) {
        $message = $isPinned ? 'Đã ghim cuộc trò chuyện!' : 'Đã bỏ ghim cuộc trò chuyện!';
        echo json_encode(['success' => true, 'message' => $message, 'isPinned' => (bool)$isPinned]);
    } else {
        echo json_encode(['success' => false, 'message' => 'Không thể cập nhật trạng thái ghim!']);
    }
}

$conn->close();
?>
