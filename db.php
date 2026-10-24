<?php
$host = "localhost";
$user = "root";
$pass = "";
$db_name = "menadzer_subskrypcji";

$conn = new mysqli($host, $user, $pass, $db_name);

if ($conn->connect_error) {
    echo json_encode(["success" => false, "message" => "Błąd połączenia z bazą danych."]);
    exit;
}

// Ustawienie kodowania znaków na UTF-8
$conn->set_charset("utf8mb4");
?>