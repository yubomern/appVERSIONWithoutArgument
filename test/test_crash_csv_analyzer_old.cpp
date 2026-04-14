/*
 * test_crash_csv_analyzer.cpp - Analyse des crashes depuis le CSV
 * Lit le fichier crash_report.csv et génère des statistiques
 * 
 * Usage:
 *   ./test_crash_csv_analyzer [chemin_vers_csv]
 *   Par défaut: lit ../crash_simulator/build/crash_report.csv
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <iomanip>
#include <ctime>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <sys/stat.h>
#endif

#define min(a,b) (((a) < (b)) ? (a) : (b))
#define max(a,b) (((a) > (b)) ? (a) : (b))


// ─── Structure pour stocker un crash ─────────────────────────────────────────
struct CrashData {
    std::string timestamp;
    long unix_timestamp;
    int category;
    std::string category_name;
    unsigned int seed;
    std::string description;
    int call_chain_depth;
    uint32_t exception_code;
    int intensity;
    int recursion_depth;
    size_t memory_size;
    bool random_mode;
    bool generate_minidump;
};

// ─── Fonctions utilitaires ───────────────────────────────────────────────────

// Vérifier si un fichier existe
bool fileExists(const std::string& path) {
#ifdef _WIN32
    return GetFileAttributesA(path.c_str()) != INVALID_FILE_ATTRIBUTES;
#else
    struct stat buffer;
    return (stat(path.c_str(), &buffer) == 0);
#endif
}

// Parser une ligne CSV
std::vector<std::string> parseCSVLine(const std::string& line) {
    std::vector<std::string> result;
    std::stringstream ss(line);
    std::string cell;
    bool inQuotes = false;
    std::string currentCell;
    
    for (size_t i = 0; i < line.length(); ++i) {
        char c = line[i];
        
        if (c == '"') {
            inQuotes = !inQuotes;
        } else if (c == ',' && !inQuotes) {
            result.push_back(currentCell);
            currentCell.clear();
        } else {
            currentCell += c;
        }
    }
    result.push_back(currentCell);
    
    return result;
}

// ─── Lecteur du CSV ──────────────────────────────────────────────────────────

std::vector<CrashData> readCrashCSV(const std::string& filename) {
    std::vector<CrashData> crashes;
    std::ifstream file(filename);
    
    if (!file.is_open()) {
        std::cerr << "❌ Erreur: Impossible d'ouvrir le fichier: " << filename << "\n";
        return crashes;
    }
    
    std::string line;
    int lineNum = 0;
    
    while (std::getline(file, line)) {
        lineNum++;
        
        // Ignorer l'en-tête
        if (lineNum == 1) continue;
        
        // Ignorer les lignes vides
        if (line.empty()) continue;
        
        std::vector<std::string> cells = parseCSVLine(line);
        
        if (cells.size() < 13) {
            std::cerr << "⚠️  Ligne " << lineNum << ": Format invalide (" 
                      << cells.size() << " colonnes au lieu de 13)\n";
            continue;
        }
        
        try {
            CrashData crash;
            crash.timestamp = cells[0];
            crash.unix_timestamp = std::stol(cells[1]);
            crash.category = std::stoi(cells[2]);
            crash.category_name = cells[3];
            crash.seed = static_cast<unsigned int>(std::stoul(cells[4]));
            crash.description = cells[5];
            crash.call_chain_depth = std::stoi(cells[6]);
            crash.exception_code = static_cast<uint32_t>(std::stoul(cells[7]));
            crash.intensity = std::stoi(cells[8]);
            crash.recursion_depth = std::stoi(cells[9]);
            crash.memory_size = std::stoull(cells[10]);
            crash.random_mode = (cells[11] == "true");
            crash.generate_minidump = (cells[12] == "true");
            
            crashes.push_back(crash);
        } catch (const std::exception& e) {
            std::cerr << "⚠️  Ligne " << lineNum << ": Erreur de parsing: " << e.what() << "\n";
        }
    }
    
    file.close();
    return crashes;
}

// ─── Analyseurs ──────────────────────────────────────────────────────────────

void printGeneralStats(const std::vector<CrashData>& crashes) {
    std::cout << "\n╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║            📊 STATISTIQUES GÉNÉRALES                      ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    std::cout << "📁 Total crashes analysés: " << crashes.size() << "\n\n";
    
    if (crashes.empty()) return;
    
    // Calculer les min/max
    int minIntensity = crashes[0].intensity;
    int maxIntensity = crashes[0].intensity;
    int totalIntensity = 0;
    
    int maxRecursion = 0;
    size_t maxMemory = 0;
    
    for (const auto& crash : crashes) {
        minIntensity = min(minIntensity, crash.intensity);
        maxIntensity = max(maxIntensity, crash.intensity);
        totalIntensity += crash.intensity;
        
        maxRecursion = max(maxRecursion, crash.recursion_depth);
        maxMemory = max(maxMemory, crash.memory_size);
    }
    
    std::cout << "📈 Intensité:\n";
    std::cout << "   • Minimum: " << minIntensity << "/10\n";
    std::cout << "   • Maximum: " << maxIntensity << "/10\n";
    std::cout << "   • Moyenne: " << std::fixed << std::setprecision(1) 
              << (static_cast<double>(totalIntensity) / crashes.size()) << "/10\n\n";
    
    std::cout << "📊 Profondeur de récursion max: " << maxRecursion << "\n";
    std::cout << "💾 Mémoire max allouée: " << (maxMemory / 1024) << " KB\n\n";
}

void printCategoryDistribution(const std::vector<CrashData>& crashes) {
    std::map<std::string, int> categoryCount;
    
    for (const auto& crash : crashes) {
        categoryCount[crash.category_name]++;
    }
    
    std::cout << "\n╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║         📋 RÉPARTITION PAR CATÉGORIE                      ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    // Trier par nombre de crashes (décroissant)
    std::vector<std::pair<std::string, int>> sortedCategories(
        categoryCount.begin(), categoryCount.end());
    
    std::sort(sortedCategories.begin(), sortedCategories.end(),
        [](const auto& a, const auto& b) { return a.second > b.second; });
    
    int total = crashes.size();
    for (const auto& [category, count] : sortedCategories) {
        double percentage = (static_cast<double>(count) / total) * 100;
        
        std::cout << std::left << std::setw(35) << category << " : ";
        std::cout << std::right << std::setw(3) << count << " ";
        
        // Barre de progression
        int barLength = 20;
        int filledLength = static_cast<int>(percentage / 5);
        
        std::cout << "[";
        for (int i = 0; i < barLength; ++i) {
            if (i < filledLength) {
                std::cout << "█";
            } else {
                std::cout << " ";
            }
        }
        std::cout << "] " << std::fixed << std::setprecision(1) << percentage << "%\n";
    }
    std::cout << "\n";
}

void printSeverityAnalysis(const std::vector<CrashData>& crashes) {
    std::map<int, int> severityCount;
    
    // Mapping catégorie -> sévérité
    std::map<int, int> categorySeverity = {
        {0, 4}, {1, 4}, {2, 3}, {3, 4}, {4, 4},
        {5, 2}, {6, 3}, {7, 3}, {8, 3}, {9, 4},
        {10, 2}, {11, 4}
    };
    
    for (const auto& crash : crashes) {
        int severity = categorySeverity[crash.category];
        severityCount[severity]++;
    }
    
    std::cout << "\n╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║         ⚠️  ANALYSE PAR SÉVÉRITÉ                          ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    std::map<int, std::string> severityLabels = {
        {1, "LOW"},
        {2, "MEDIUM"},
        {3, "HIGH"},
        {4, "CRITICAL"}
    };
    
    std::map<int, std::string> severityColors = {
        {1, "🟢"},
        {2, "🟡"},
        {3, "🟠"},
        {4, "🔴"}
    };
    
    for (int sev = 4; sev >= 1; --sev) {
        if (severityCount.find(sev) != severityCount.end()) {
            std::cout << severityColors[sev] << " " 
                      << std::left << std::setw(10) << severityLabels[sev] 
                      << " : " << severityCount[sev] << " crashes\n";
        }
    }
    std::cout << "\n";
}

void printTimelineAnalysis(const std::vector<CrashData>& crashes) {
    if (crashes.empty()) return;
    
    std::cout << "\n╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║         ⏱️  ANALYSE TEMPORELLE                            ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    // Premier et dernier crash
    std::cout << "🕐 Premier crash: " << crashes.front().timestamp << "\n";
    std::cout << "🕐 Dernier crash: " << crashes.back().timestamp << "\n";
    
    if (crashes.size() > 1) {
        long duration = crashes.back().unix_timestamp - crashes.front().unix_timestamp;
        std::cout << "⏱️  Durée totale: " << duration << " secondes\n";
        
        if (duration > 0) {
            double rate = static_cast<double>(crashes.size()) / duration;
            std::cout << "📊 Fréquence: " << std::fixed << std::setprecision(2) 
                      << rate << " crashes/seconde\n";
        }
    }
    std::cout << "\n";
}

void printTopCrashes(const std::vector<CrashData>& crashes) {
    if (crashes.empty()) return;
    
    std::cout << "\n╔══════════════════════════════════════════════════════════╗\n";
    std::cout << "║         🏆 TOP 5 DES CRASHS LES PLUS FRÉQUENTS            ║\n";
    std::cout << "╚══════════════════════════════════════════════════════════╝\n\n";
    
    std::map<std::string, int> crashTypes;
    for (const auto& crash : crashes) {
        std::string key = crash.category_name + " (Intensité: " + 
                         std::to_string(crash.intensity) + ")";
        crashTypes[key]++;
    }
    
    std::vector<std::pair<std::string, int>> sortedTypes(
        crashTypes.begin(), crashTypes.end());
    
    std::sort(sortedTypes.begin(), sortedTypes.end(),
        [](const auto& a, const auto& b) { return a.second > b.second; });
    
    int count = 0;
    for (const auto& [type, occurrences] : sortedTypes) {
        if (count++ >= 5) break;
        
        std::cout << (count == 1 ? "🥇" : count == 2 ? "🥈" : count == 3 ? "🥉" : "  ")
                  << " #" << count << " " << type << "\n";
        std::cout << "     → " << occurrences << " occurrence(s)\n\n";
    }
}

void exportAnalysisToCSV(const std::vector<CrashData>& crashes, 
                         const std::string& outputPath) {
    std::ofstream out(outputPath);
    if (!out.is_open()) {
        std::cerr << "❌ Erreur: Impossible de créer " << outputPath << "\n";
        return;
    }
    
    // Statistiques par catégorie
    std::map<std::string, int> categoryCount;
    std::map<std::string, double> categoryAvgIntensity;
    std::map<std::string, int> categoryTotalIntensity;
    
    for (const auto& crash : crashes) {
        categoryCount[crash.category_name]++;
        categoryTotalIntensity[crash.category_name] += crash.intensity;
    }
    
    for (auto& [category, total] : categoryTotalIntensity) {
        categoryAvgIntensity[category] = static_cast<double>(total) / categoryCount[category];
    }
    
    // Écriture CSV
    out << "category,total_crashes,average_intensity,percentage\n";
    
    for (const auto& [category, count] : categoryCount) {
        double percentage = (static_cast<double>(count) / crashes.size()) * 100;
        out << "\"" << category << "\","
            << count << ","
            << std::fixed << std::setprecision(2) << categoryAvgIntensity[category] << ","
            << std::fixed << std::setprecision(2) << percentage << "\n";
    }
    
    out.close();
    std::cout << "\n💾 Rapport exporté vers: " << outputPath << "\n";
}

// ─── Main ────────────────────────────────────────────────────────────────────

void printUsage(const char* programName) {
    std::cout << "Usage: " << programName << " [chemin_vers_csv] [--export]\n\n";
    std::cout << "Arguments:\n";
    std::cout << "  chemin_vers_csv    Chemin vers le fichier crash_report.csv\n";
    std::cout << "                     (défaut: ../crash_simulator/build/crash_report.csv)\n";
    std::cout << "  --export           Exporter l'analyse vers analysis_report.csv\n";
}

int main(int argc, char* argv[]) {
    std::cout << "╔════════════════════════════════════════════════════════════════╗\n";
    std::cout << "║     📊 CRASH CSV ANALYZER - Analyse des rapports de crash      ║\n";
    std::cout << "╚════════════════════════════════════════════════════════════════╝\n";
    
    // Parser les arguments
    std::string csvPath = "../crash_simulator/build/crash_report.csv";
    bool exportReport = false;
    
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        } else if (arg == "--export") {
            exportReport = true;
        } else if (arg[0] != '-') {
            csvPath = arg;
        }
    }
    
    // Vérifier si le fichier existe
    if (!fileExists(csvPath)) {
        std::cerr << "\n❌ Erreur: Le fichier '" << csvPath << "' n'existe pas.\n";
        std::cerr << "\n💡 Astuce: Lancez d'abord le crash_simulator pour générer le CSV.\n";
        std::cerr << "   Exemple: cd ../crash_simulator/build && ./crash-simulator --category 1\n";
        return 1;
    }
    
    std::cout << "\n📂 Lecture du fichier: " << csvPath << "\n";
    
    // Lire le CSV
    std::vector<CrashData> crashes = readCrashCSV(csvPath);
    
    if (crashes.empty()) {
        std::cerr << "⚠️  Aucune donnée à analyser.\n";
        return 0;
    }
    
    // Afficher les analyses
    printGeneralStats(crashes);
    printCategoryDistribution(crashes);
    printSeverityAnalysis(crashes);
    printTimelineAnalysis(crashes);
    printTopCrashes(crashes);
    
    // Export optionnel
    if (exportReport) {
        exportAnalysisToCSV(crashes, "analysis_report.csv");
    }
    
    std::cout << "\n✨ Analyse terminée avec succès!\n\n";
    
    return 0;
}