package com.peanutbutter1001.saramcrawler.data.model

import kotlinx.serialization.Serializable

@Serializable
data class StatsData(
    val viewedRecIdxs: Set<String> = emptySet(),
    val keywordCounts: Map<String, Int> = emptyMap()
)
