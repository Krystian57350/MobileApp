<?php
// Uruchamia moduł Pythona (raporty/run.py) i zwraca wynik jako tablicę PHP.
// Ścieżkę można nadpisać zmienną środowiskową PYTHON_BIN.
$pythonBin = getenv('PYTHON_BIN');
if (!$pythonBin) {
    $localAppData = getenv('LOCALAPPDATA');
    $pythonBin = $localAppData
        ? $localAppData . '\\Programs\\Python\\Python315\\python.exe'
        : 'python';
}
define('PYTHON_BIN', $pythonBin);

const REPORT_GRANULARITIES = ['month', 'quarter', 'half', 'year'];

function validReportDate($value) {
    return $value === '' || (preg_match('/^\d{4}-\d{2}-\d{2}$/', $value) && strtotime($value) !== false);
}

/**
 * @param string $format 'json' lub 'pdf'
 * @param string $pdfPath ścieżka wyjściowa PDF (tylko dla 'pdf')
 */
function runReport(int $userId, string $username, string $granularity, string $from, string $to,
                   string $format, string $pdfPath = ''): array {
    // walidacja po stronie PHP - do powłoki trafiają tylko sprawdzone wartości
    if (!in_array($granularity, REPORT_GRANULARITIES, true)) {
        return ['success' => false, 'message' => 'Nieprawidłowy podział czasowy.'];
    }
    if (!validReportDate($from) || !validReportDate($to)) {
        return ['success' => false, 'message' => 'Nieprawidłowy format daty (RRRR-MM-DD).'];
    }
    if ($from !== '' && $to !== '' && $from > $to) {
        return ['success' => false, 'message' => 'Data początkowa jest późniejsza niż końcowa.'];
    }

    $cmd = escapeshellarg(PYTHON_BIN) . ' ' . escapeshellarg(__DIR__ . DIRECTORY_SEPARATOR . 'run.py')
         . ' --user-id ' . (int)$userId
         . ' --username ' . escapeshellarg($username)
         . ' --granularity ' . escapeshellarg($granularity)
         . ' --from ' . escapeshellarg($from)
         . ' --to ' . escapeshellarg($to)
         . ' --format ' . escapeshellarg($format);
    if ($format === 'pdf') {
        $cmd .= ' --output ' . escapeshellarg($pdfPath);
    }

    $output = [];
    $code = 0;
    exec($cmd . ' 2>&1', $output, $code);
    $text = trim(implode("\n", $output));
    $result = json_decode($text, true);

    if (!is_array($result)) {
        return ['success' => false,
                'message' => 'Nie udało się uruchomić Pythona. Sprawdź instalację i PYTHON_BIN. ' . substr($text, 0, 300)];
    }
    return $result;
}
