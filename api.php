<?php
header("Access-Control-Allow-Origin: *"); // Allow access from any origin
header("Content-Type: application/json"); // Set JSON header by default

// Define file paths
$filteredCoinsFile = "filtered_top_100_coins.csv";
$newCryptosFile = "new_cryptocurrencies.csv";
$screenshotsFolder = "twitter_screenshots";

// Check for requested file type
if (isset($_GET['file'])) {
    $file = $_GET['file'];

    if ($file === "filtered_top_100_coins") {
        if (file_exists($filteredCoinsFile)) {
            header("Content-Type: text/csv");
            header("Content-Disposition: attachment; filename=filtered_top_100_coins.csv");
            readfile($filteredCoinsFile);
            exit;
        } else {
            echo json_encode(["status" => "error", "message" => "File not found: filtered_top_100_coins.csv"]);
            exit;
        }
    } elseif ($file === "new_cryptocurrencies") {
        if (file_exists($newCryptosFile)) {
            header("Content-Type: text/csv");
            header("Content-Disposition: attachment; filename=new_cryptocurrencies.csv");
            readfile($newCryptosFile);
            exit;
        } else {
            echo json_encode(["status" => "error", "message" => "File not found: new_cryptocurrencies.csv"]);
            exit;
        }
    } elseif ($file === "twitter_screenshots") {
        if (is_dir($screenshotsFolder)) {
            $zipFile = "twitter_screenshots.zip";

            // Create a ZIP archive of the folder
            $zip = new ZipArchive();
            if ($zip->open($zipFile, ZipArchive::CREATE | ZipArchive::OVERWRITE) === TRUE) {
                $files = array_diff(scandir($screenshotsFolder), ['.', '..']);
                foreach ($files as $file) {
                    $filePath = $screenshotsFolder . DIRECTORY_SEPARATOR . $file;
                    if (is_file($filePath)) {
                        $zip->addFile($filePath, $file);
                    }
                }
                $zip->close();

                // Serve the ZIP file for download
                header("Content-Type: application/zip");
                header("Content-Disposition: attachment; filename=$zipFile");
                header("Content-Length: " . filesize($zipFile));
                readfile($zipFile);

                // Delete the ZIP file after serving
                unlink($zipFile);
                exit;
            } else {
                echo json_encode(["status" => "error", "message" => "Failed to create ZIP file"]);
                exit;
            }
        } else {
            echo json_encode(["status" => "error", "message" => "Folder not found: twitter_screenshots"]);
            exit;
        }
    } else {
        echo json_encode(["status" => "error", "message" => "Invalid file request"]);
        exit;
    }
}

// Default API response
$dane = [
    "status" => "success",
    "message" => "Witaj! To jest moje API",
    "data" => [
        "id" => 1,
        "name" => "Testowy użytkownik",
        "email" => "test@example.com"
    ]
];

echo json_encode($dane);
?>
