package com.peanutbutter1001.saramcrawler.data.model

import kotlinx.serialization.Serializable

@Serializable
data class JobItem(
    val corpName: String,
    val title: String,
    val link: String,
    val condition: String,
    val sector: String,
    val deadline: String,
    val recIdx: String
)
