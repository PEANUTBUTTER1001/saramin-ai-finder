package com.peanutbutter1001.saramin_ai_finder.data.model

import kotlinx.serialization.Serializable

@Serializable
data class StatsData(
    val viewedRecIdxs: Set<String> = emptySet(),
    val keywordCounts: Map<String, Int> = emptyMap()
)
