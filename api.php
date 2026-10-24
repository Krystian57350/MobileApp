<?php
header('Content-Type: application/json');
session_start();
include('db.php');
require_once __DIR__ . '/raporty/run_report.php';

// Pobranie danych przesłanych w formacie JSON
$input = json_decode(file_get_contents('php://input'), true);
$action = $input['action'] ?? $_GET['action'] ?? '';

// Pomocnicza funkcja do pobierania ID zalogowanego użytkownika z sesji
function getUserId() {
    return $_SESSION['user_id'] ?? null;
}

switch ($action) {
    case 'register':
        $user = mysqli_real_escape_string($conn, $input['username']);
        $pass = $input['password'];

        if (strlen($pass) < 3) {
            echo json_encode(["success" => false, "message" => "Hasło za krótkie"]);
            exit;
        }

        // Sprawdzenie czy użytkownik istnieje
        $check = $conn->query("SELECT id FROM uzytkownicy WHERE username = '$user'");
        if ($check->num_rows > 0) {
            echo json_encode(["success" => false, "code" => "exists", "message" => "Użytkownik istnieje"]);
        } else {
            $hash = password_hash($pass, PASSWORD_DEFAULT);
            $sql = "INSERT INTO uzytkownicy (username, password) VALUES ('$user', '$hash')";
            if ($conn->query($sql)) {
                $newUserId = $conn->insert_id;
                $defaultCats = ["Wideo", "Muzyka", "Aplikacje"];
                foreach ($defaultCats as $cat) {
                    $catEscaped = mysqli_real_escape_string($conn, $cat);
                    $conn->query("INSERT INTO kategorie (user_id, nazwa) VALUES ($newUserId, '$catEscaped')");
                }
                echo json_encode(["success" => true]);
            } else {
                echo json_encode(["success" => false, "message" => "Błąd rejestracji"]);
            }
        }
        break;

    case 'login':
        $user = mysqli_real_escape_string($conn, $input['username']);
        $pass = $input['password'];

        $result = $conn->query("SELECT id, username, password FROM uzytkownicy WHERE username = '$user'");
        if ($result->num_rows > 0) {
            $row = $result->fetch_assoc();
            $stored = $row['password'];
            if (password_verify($pass, $stored)) {
                $_SESSION['user_id'] = $row['id'];
                $_SESSION['username'] = $row['username'];
                echo json_encode(["success" => true, "username" => $row['username']]);
                break;
            }
            // Wsparcie dla istniejących haseł przechowywanych w jawnym tekście
            if ($stored === $pass) {
                $hashed = password_hash($pass, PASSWORD_DEFAULT);
                $conn->query("UPDATE uzytkownicy SET password = '$hashed' WHERE id = {$row['id']}");
                $_SESSION['user_id'] = $row['id'];
                $_SESSION['username'] = $row['username'];
                echo json_encode(["success" => true, "username" => $row['username']]);
                break;
            }
        }
        echo json_encode(["success" => false, "message" => "Błędny login lub hasło"]);
        break;

    case 'logout':
        session_destroy();
        echo json_encode(["success" => true]);
        break;

    case 'check_session':
        if (isset($_SESSION['username'])) {
            echo json_encode(["success" => true, "username" => $_SESSION['username']]);
        } else {
            echo json_encode(["success" => false]);
        }
        break;

    case 'get_data':
        $userId = getUserId();
        if (!$userId) { echo json_encode(["success" => false]); exit; }

        // Pobieranie kategorii
        $categories = [];
        $resCat = $conn->query("SELECT nazwa FROM kategorie WHERE user_id = $userId");
        while($row = $resCat->fetch_assoc()) { $categories[] = $row['nazwa']; }
        if (empty($categories)) {
            $defaultCats = ["Wideo", "Muzyka", "Aplikacje"];
            foreach ($defaultCats as $cat) {
                $catEscaped = mysqli_real_escape_string($conn, $cat);
                $conn->query("INSERT INTO kategorie (user_id, nazwa) VALUES ($userId, '$catEscaped')");
                $categories[] = $cat;
            }
        }

        // Pobieranie subskrypcji
        $subs = [];
        $resSubs = $conn->query("SELECT id, name, cost, period, nextDate, category, note, active, added FROM subskrypcje WHERE user_id = $userId");
        while($row = $resSubs->fetch_assoc()) {
            $row['cost'] = (float)$row['cost'];
            $row['active'] = (bool)$row['active'];
            $row['added'] = (int)$row['added'];
            $subs[] = $row;
        }

        echo json_encode(["success" => true, "categories" => $categories, "subs" => $subs]);
        break;

    case 'save_subscription':
        $userId = getUserId();
        if (!$userId) { echo json_encode(["success" => false]); exit; }

        $id = mysqli_real_escape_string($conn, $input['id']);
        $name = mysqli_real_escape_string($conn, $input['name']);
        $cost = (float)$input['cost'];
        $period = mysqli_real_escape_string($conn, $input['period']);
        $nextDate = $input['nextDate'] ? "'".mysqli_real_escape_string($conn, $input['nextDate'])."'" : "NULL";
        $category = mysqli_real_escape_string($conn, $input['category']);
        $note = mysqli_real_escape_string($conn, $input['note']);
        $active = $input['active'] ? 1 : 0;
        $added = (int)$input['added'];

        // Sprawdź czy to aktualizacja czy nowy wpis
        $check = $conn->query("SELECT id FROM subskrypcje WHERE id = '$id' AND user_id = $userId");
        if ($check->num_rows > 0) {
            $sql = "UPDATE subskrypcje SET name='$name', cost=$cost, period='$period', nextDate=$nextDate, category='$category', note='$note', active=$active WHERE id='$id' AND user_id=$userId";
        } else {
            $sql = "INSERT INTO subskrypcje (id, user_id, name, cost, period, nextDate, category, note, active, added) VALUES ('$id', $userId, '$name', $cost, '$period', $nextDate, '$category', '$note', $active, $added)";
        }

        if ($conn->query($sql)) { echo json_encode(["success" => true]); } 
        else { echo json_encode(["success" => false, "message" => $conn->error]); }
        break;

    case 'delete_subscription':
        $userId = getUserId();
        $id = mysqli_real_escape_string($conn, $input['id']);
        $conn->query("DELETE FROM subskrypcje WHERE id='$id' AND user_id=$userId");
        echo json_encode(["success" => true]);
        break;

    case 'add_category':
        $userId = getUserId();
        $name = mysqli_real_escape_string($conn, $input['name']);
        
        $sql = "INSERT INTO kategorie (user_id, nazwa) VALUES ($userId, '$name')";
        if($conn->query($sql)) { echo json_encode(["success" => true]); }
        else { echo json_encode(["success" => false, "message" => "Kategoria już istnieje"]); }
        break;

    case 'clear_all':
        $userId = getUserId();
        $conn->query("DELETE FROM subskrypcje WHERE user_id=$userId");
        echo json_encode(["success" => true]);
        break;

    case 'report_data':
    case 'report_pdf':
        $userId = getUserId();
        if (!$userId) { echo json_encode(["success" => false, "message" => "Brak sesji."]); exit; }
        $gran = (string)($input['granularity'] ?? $_GET['granularity'] ?? 'month');
        $from = (string)($input['from'] ?? $_GET['from'] ?? '');
        $to   = (string)($input['to'] ?? $_GET['to'] ?? '');
        $uname = $_SESSION['username'] ?? '';
        session_write_close(); // Python może chwilę działać - nie blokuj sesji

        if ($action === 'report_data') {
            echo json_encode(runReport((int)$userId, $uname, $gran, $from, $to, 'json'), JSON_UNESCAPED_UNICODE);
            break;
        }
        $tmp = tempnam(sys_get_temp_dir(), 'rap');
        $res = runReport((int)$userId, $uname, $gran, $from, $to, 'pdf', $tmp);
        if (!empty($res['success']) && is_file($tmp) && filesize($tmp) > 0) {
            header('Content-Type: application/pdf');
            header('Content-Disposition: attachment; filename="raport_wydatkow_' . date('Y-m-d') . '.pdf"');
            header('Content-Length: ' . filesize($tmp));
            readfile($tmp);
        } else {
            echo json_encode(["success" => false, "message" => $res['message'] ?? 'Nie udało się wygenerować PDF.'], JSON_UNESCAPED_UNICODE);
        }
        @unlink($tmp);
        break;

    default:
        echo json_encode(["success" => false, "message" => "Nieznana akcja"]);
        break;
}
?>