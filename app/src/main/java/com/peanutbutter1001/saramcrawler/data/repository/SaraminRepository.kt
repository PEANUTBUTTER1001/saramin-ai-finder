package com.peanutbutter1001.saramcrawler.data.repository

import android.content.Context
import com.peanutbutter1001.saramcrawler.data.model.JobDetails
import com.peanutbutter1001.saramcrawler.data.model.JobItem
import com.peanutbutter1001.saramcrawler.data.model.StatsData
import com.peanutbutter1001.saramcrawler.utils.HtmlParser
import com.peanutbutter1001.saramcrawler.utils.TechKeywords
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.jsoup.Jsoup
import java.io.File

class SaraminRepository(
    private val context: Context? = null
) {

    companion object {
        private const val SARAMIN_SEARCH_URL = "https://www.saramin.co.kr/zf_user/search/recruit"
        private const val SARAMIN_DETAIL_API_URL = "https://www.saramin.co.kr/zf_user/jobs/relay/view-detail"
        private const val USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        private const val CACHE_FILE_NAME = "jobs_cache.json"
        private const val STATS_FILE_NAME = "viewed_stats.json"
    }

    private val cacheFile: File
        get() = if (context != null) {
            File(context.cacheDir, CACHE_FILE_NAME)
        } else {
            File(System.getProperty("java.io.tmpdir"), CACHE_FILE_NAME)
        }

    private val statsFile: File
        get() = if (context != null) {
            File(context.cacheDir, STATS_FILE_NAME)
        } else {
            File(System.getProperty("java.io.tmpdir"), STATS_FILE_NAME)
        }

    // Save jobs to cache file
    fun saveCache(jobs: List<JobItem>) {
        try {
            val jsonString = Json.encodeToString(jobs)
            cacheFile.writeText(jsonString)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // Load jobs from cache file
    fun loadCache(): List<JobItem> {
        return try {
            if (cacheFile.exists()) {
                val jsonString = cacheFile.readText()
                Json.decodeFromString<List<JobItem>>(jsonString)
            } else {
                emptyList()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            emptyList()
        }
    }

    // Load cumulative stats
    fun loadStats(): StatsData {
        return try {
            if (statsFile.exists()) {
                val jsonString = statsFile.readText()
                Json.decodeFromString<StatsData>(jsonString)
            } else {
                StatsData()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            StatsData()
        }
    }

    // Save cumulative stats
    fun saveStats(stats: StatsData) {
        try {
            val jsonString = Json.encodeToString(stats)
            statsFile.writeText(jsonString)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // Reset stats
    fun clearStats() {
        try {
            if (statsFile.exists()) {
                statsFile.delete()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // Record job view and extract stats
    fun recordJobView(jobItem: JobItem, details: JobDetails) {
        if (jobItem.recIdx.isEmpty()) return

        val currentStats = loadStats()
        // Avoid double counting this job posting
        if (currentStats.viewedRecIdxs.contains(jobItem.recIdx)) return

        val targetText = "${details.qualifications} ${details.preferences}"
        val matchedKeywords = mutableSetOf<String>()
 
        for ((keyword, regexList) in TechKeywords.KEYWORD_PATTERNS) {
            for (regex in regexList) {
                if (regex.containsMatchIn(targetText)) {
                    matchedKeywords.add(keyword)
                    break // Stop checking synonyms once matched (max 1 count per page/posting)
                }
            }
        }

        // Update counts
        val newKeywordCounts = currentStats.keywordCounts.toMutableMap()
        for (keyword in matchedKeywords) {
            newKeywordCounts[keyword] = (newKeywordCounts[keyword] ?: 0) + 1
        }

        val updatedStats = StatsData(
            viewedRecIdxs = currentStats.viewedRecIdxs + jobItem.recIdx,
            keywordCounts = newKeywordCounts
        )
        saveStats(updatedStats)
    }

    suspend fun getJobs(searchword: String, maxPages: Int = 3): List<JobItem> = withContext(Dispatchers.IO) {
        val filteredJobs = mutableListOf<JobItem>()
        var currentPage = 1

        while (currentPage <= maxPages) {
            try {
                val document = Jsoup.connect(SARAMIN_SEARCH_URL)
                    .userAgent(USER_AGENT)
                    .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8")
                    .header("Accept-Language", "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7")
                    .data("searchword", searchword)
                    .data("loc_mcd", "101000") // 서울 전체
                    .data("exp_cd", "1,2")     // 신입, 경력
                    .data("exp_max", "3")      // 3년 이하
                    .data("edu_cd", "0,4")     // 학력무관, 대졸(4년)
                    .data("recruitPage", currentPage.toString())
                    .data("recruitSort", "relation")
                    .data("recruitPageCount", "40")
                    .timeout(10000)
                    .maxBodySize(0)
                    .get()

                val jobElements = document.select("div.item_recruit")
                if (jobElements.isEmpty()) {
                    break
                }

                for (element in jobElements) {
                    val corpName = element.selectFirst("strong.corp_name")?.text()?.trim() ?: "N/A"
                    val aTag = element.selectFirst("h2.job_tit a")
                    val title = aTag?.attr("title")?.takeIf { it.isNotEmpty() } ?: aTag?.text()?.trim() ?: "N/A"
                    val link = aTag?.attr("href")?.let { "https://www.saramin.co.kr$it" } ?: "N/A"

                    // Parse recIdx from link using Regex
                    val recIdx = Regex("rec_idx=(\\d+)").find(link)?.groupValues?.get(1) ?: ""

                    val conditionTag = element.selectFirst("div.job_condition")
                    val conditions = conditionTag?.select("span")?.map { it.text().trim() } ?: emptyList()
                    val conditionsText = conditions.joinToString(", ")

                    val sectorTag = element.selectFirst("div.job_sector")
                    sectorTag?.select("span.job_day")?.forEach { it.remove() }
                    val sectorText = sectorTag?.text()?.trim()?.replace(Regex("\\s+"), " ") ?: "N/A"

                    val dateTag = element.selectFirst("div.job_date")
                    val deadline = dateTag?.selectFirst("span.date")?.text()?.trim() ?: "N/A"

                    // Filtering Logic
                    if (!HtmlParser.isValidEducation(conditions)) {
                        continue
                    }

                    if (!HtmlParser.isValidJob(sectorText, title, searchword)) {
                        continue
                    }

                    filteredJobs.add(
                        JobItem(
                            corpName = corpName,
                            title = title,
                            link = link,
                            condition = conditionsText,
                            sector = sectorText,
                            deadline = deadline,
                            recIdx = recIdx
                        )
                    )
                }

                if (jobElements.size < 40) {
                    break
                }

                currentPage++
                delay(500)
            } catch (e: Exception) {
                e.printStackTrace()
                break
            }
        }

        // Save successfully crawled data to cache
        if (filteredJobs.isNotEmpty()) {
            saveCache(filteredJobs)
        }

        filteredJobs
    }

    suspend fun getJobDetails(recIdx: String): JobDetails = withContext(Dispatchers.IO) {
        if (recIdx.isEmpty()) return@withContext JobDetails("정보 없음", "정보 없음", "정보 없음")
        
        try {
            val document = Jsoup.connect(SARAMIN_DETAIL_API_URL)
                .userAgent(USER_AGENT)
                .data("rec_idx", recIdx)
                .timeout(10000)
                .maxBodySize(0)
                .get()

            val text = document.text().replace(Regex("\\s+"), " ")

            // Check if it's an image-only posting
            if (text.length < 100 && document.selectFirst("img") != null) {
                return@withContext JobDetails("상세 이미지 참고", "상세 이미지 참고", "상세 이미지 참고")
            }

            val mainWork = HtmlParser.extractSection(
                text,
                listOf("주요업무", "주요 업무", "담당업무", "담당 업무", "포지션 상세"),
                listOf("자격요건", "자격 요건", "우대사항", "우대 사항", "혜택 및 복지", "근무환경", "전형절차")
            )

            val qualifications = HtmlParser.extractSection(
                text,
                listOf("자격요건", "자격 요건", "지원자격", "지원 자격"),
                listOf("우대사항", "우대 사항", "혜택 및 복지", "근무환경", "전형절차")
            )

            val preferences = HtmlParser.extractSection(
                text,
                listOf("우대사항", "우대 사항"),
                listOf("혜택 및 복지", "근무환경", "전형절차", "유의사항", "복리후생")
            )

            JobDetails(
                mainWork = mainWork,
                qualifications = qualifications,
                preferences = preferences
            )
        } catch (e: Exception) {
            e.printStackTrace()
            JobDetails("오류 발생 (상세 로드 실패)", "오류 발생 (상세 로드 실패)", "오류 발생 (상세 로드 실패)")
        }
    }
}
