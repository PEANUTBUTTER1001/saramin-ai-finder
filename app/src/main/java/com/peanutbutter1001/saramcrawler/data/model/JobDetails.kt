package com.peanutbutter1001.saramcrawler.data.model

import kotlinx.serialization.Serializable

@Serializable
data class JobDetails(
    val mainWork: String,
    val qualifications: String,
    val preferences: String
)
