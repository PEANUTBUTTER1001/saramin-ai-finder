package com.peanutbutter1001.saramin_ai_finder.utils

object HtmlParser {
    fun extractSection(text: String, startKeywords: List<String>, endKeywords: List<String>): String {
        var startIdx = -1
        for (k in startKeywords) {
            val idx = text.indexOf(k)
            if (idx != -1) {
                startIdx = idx + k.length
                break
            }
        }
        if (startIdx == -1) return "정보 없음"

        var endIdx = text.length
        for (k in endKeywords) {
            val idx = text.indexOf(k, startIdx)
            if (idx != -1 && idx < endIdx) {
                endIdx = idx
            }
        }

        val result = text.substring(startIdx, endIdx).trim()
        return result.takeIf { it.isNotEmpty() } ?: "정보 없음"
    }

    fun isValidEducation(conditions: List<String>): Boolean {
        for (cond in conditions) {
            if (cond.contains("학력무관") || cond.contains("무관")) {
                return true
            }
            if (cond.contains("대졸") && cond.contains("4년")) {
                return true
            }
            if (cond.contains("대학교") && cond.contains("4년")) {
                return true
            }
            if (cond == "대졸(4년)↑" || cond == "대졸(4년)") {
                return true
            }
        }
        return false
    }

    fun isValidJob(sectorText: String, title: String, searchword: String): Boolean {
        val upperSearch = searchword.uppercase()
        val upperSector = sectorText.uppercase()
        val upperTitle = title.uppercase()

        if (upperSearch.contains("AI") || upperSearch.contains("인공지능") || upperSearch.contains("인공 지능")) {
            return upperSector.contains("AI") || upperSector.contains("인공지능") || upperSector.contains("인공 지능") ||
                   upperTitle.contains("AI") || upperTitle.contains("인공지능") || upperTitle.contains("인공 지능")
        }

        return upperSector.contains(upperSearch) || upperTitle.contains(upperSearch)
    }
}
