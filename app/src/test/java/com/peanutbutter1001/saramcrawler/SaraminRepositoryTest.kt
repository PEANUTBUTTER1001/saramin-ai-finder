package com.peanutbutter1001.saramcrawler

import com.peanutbutter1001.saramcrawler.data.model.JobItem
import com.peanutbutter1001.saramcrawler.data.repository.SaraminRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SaraminRepositoryTest {

    @Test
    fun testCrawlSaraminJobs() = runBlocking {
        val repository = SaraminRepository(null)
        val jobs = repository.getJobs("AI", maxPages = 1)
        
        println("Fetched ${jobs.size} jobs from Saramin.")
        assertNotNull(jobs)
        
        if (jobs.isNotEmpty()) {
            val firstJob = jobs.first()
            println("First job: $firstJob")
            assertTrue(firstJob.corpName.isNotEmpty())
            assertTrue(firstJob.title.isNotEmpty())
            assertTrue(firstJob.link.startsWith("http"))
            assertTrue(firstJob.recIdx.isNotEmpty())
            
            // Test detail parsing with all crawled jobs to see which ones have text
            for (job in jobs) {
                println("Testing detail parsing for ${job.corpName} (idx: ${job.recIdx})...")
                val details = repository.getJobDetails(job.recIdx)
                println("Job Details for ${job.corpName}:")
                println(" - Main Work: ${details.mainWork}")
                println(" - Qualifications: ${details.qualifications}")
                println(" - Preferences: ${details.preferences}")
                println("----------------------------------------")
            }
            
            // Just assert the first job details are not null
            val details = repository.getJobDetails(jobs.first().recIdx)
            assertNotNull(details)
        }
    }

    @Test
    fun testLocalCaching() {
        val repository = SaraminRepository(null)
        val testJobs = listOf(
            JobItem(
                corpName = "Test Corp A",
                title = "AI Engineer",
                link = "https://example.com/a",
                condition = "신입, 대졸(4년)",
                sector = "인공지능, 머신러닝",
                deadline = "~ 12/31",
                recIdx = "12345"
            ),
            JobItem(
                corpName = "Test Corp B",
                title = "Data Scientist",
                link = "https://example.com/b",
                condition = "경력 2년, 학력무관",
                sector = "AI, 빅데이터",
                deadline = "상시채용",
                recIdx = "67890"
            )
        )

        // Save to cache
        repository.saveCache(testJobs)

        // Load from cache
        val cachedJobs = repository.loadCache()

        // Verify
        assertNotNull(cachedJobs)
        assertEquals(2, cachedJobs.size)
        assertEquals("Test Corp A", cachedJobs[0].corpName)
        assertEquals("AI Engineer", cachedJobs[0].title)
        assertEquals("12345", cachedJobs[0].recIdx)
        assertEquals("Test Corp B", cachedJobs[1].corpName)
        assertEquals("Data Scientist", cachedJobs[1].title)
        assertEquals("67890", cachedJobs[1].recIdx)

        println("Cache test passed successfully. Cached jobs: $cachedJobs")
    }

    @Test
    fun testStatsAccumulation() {
        val repository = SaraminRepository(null)
        repository.clearStats()

        // Check empty stats
        var stats = repository.loadStats()
        assertTrue(stats.viewedRecIdxs.isEmpty())
        assertTrue(stats.keywordCounts.isEmpty())

        // 1. Record job A (has Python, PyTorch, Docker, AWS)
        val jobA = JobItem(
            corpName = "Corp A",
            title = "Python ML Developer",
            link = "https://example.com/a?rec_idx=111",
            condition = "서울 강남구, 신입",
            sector = "AI, Python",
            deadline = "상시채용",
            recIdx = "111"
        )
        val detailsA = com.peanutbutter1001.saramcrawler.data.model.JobDetails(
            mainWork = "ML modeling",
            qualifications = "Python, PyTorch, PyTorch (duplicate check), 파이썬 (Korean synonym check)",
            preferences = "Docker, AWS"
        )

        repository.recordJobView(jobA, detailsA)

        // Verify stats
        stats = repository.loadStats()
        assertEquals(1, stats.viewedRecIdxs.size)
        assertTrue(stats.viewedRecIdxs.contains("111"))
        assertEquals(1, stats.keywordCounts["Python"]) // "Python" and "파이썬" on same page should only count 1
        assertEquals(1, stats.keywordCounts["PyTorch"])
        assertEquals(1, stats.keywordCounts["Docker"])
        assertEquals(1, stats.keywordCounts["AWS"])
        assertEquals(null, stats.keywordCounts["Java"])

        // 2. Record job A again (should ignore duplicate recIdx)
        repository.recordJobView(jobA, detailsA)
        stats = repository.loadStats()
        assertEquals(1, stats.viewedRecIdxs.size)
        assertEquals(1, stats.keywordCounts["Python"])

        // 3. Record job B (different recIdx, containing Java and JavaScript/자바스크립트)
        val jobB = JobItem(
            corpName = "Corp B",
            title = "Backend Java Developer",
            link = "https://example.com/b?rec_idx=222",
            condition = "서울 마포구, 경력",
            sector = "Java, Spring Boot",
            deadline = "상시채용",
            recIdx = "222"
        )
        val detailsB = com.peanutbutter1001.saramcrawler.data.model.JobDetails(
            mainWork = "API development",
            qualifications = "자바 실무 (Korean Java), 자바스크립트 (Korean JavaScript)",
            preferences = "Spring Boot, SQL"
        )

        repository.recordJobView(jobB, detailsB)

        // Verify accumulated stats
        stats = repository.loadStats()
        assertEquals(2, stats.viewedRecIdxs.size)
        assertTrue(stats.viewedRecIdxs.contains("222"))
        assertEquals(1, stats.keywordCounts["Python"]) // 1 (Job A)
        assertEquals(1, stats.keywordCounts["Java"]) // 1 (Job B - matched "자바" but excluded "자바스크립트")
        assertEquals(1, stats.keywordCounts["JavaScript"]) // 1 (Job B - matched "자바스크립트")
        assertEquals(1, stats.keywordCounts["Spring Boot"]) // 1 (Job B)
        assertEquals(1, stats.keywordCounts["SQL"]) // 1 (Job B)
        assertEquals(1, stats.keywordCounts["PyTorch"]) // 1 (Job A)

        // 4. Clear stats
        repository.clearStats()
        stats = repository.loadStats()
        assertTrue(stats.viewedRecIdxs.isEmpty())
        assertTrue(stats.keywordCounts.isEmpty())
        println("Stats accumulation, duplicate check, and Korean synonym matching test passed successfully.")
    }
}

