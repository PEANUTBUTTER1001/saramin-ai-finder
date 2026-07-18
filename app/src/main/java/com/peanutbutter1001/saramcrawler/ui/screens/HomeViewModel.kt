package com.peanutbutter1001.saramcrawler.ui.screens

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.peanutbutter1001.saramcrawler.data.model.JobItem
import com.peanutbutter1001.saramcrawler.data.repository.SaraminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface HomeUiState {
    object Loading : HomeUiState
    data class Success(val jobs: List<JobItem>) : HomeUiState
    data class Error(val message: String) : HomeUiState
}

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: SaraminRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private val _searchQuery = MutableStateFlow("AI")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    // Crawling state indicator flow
    private val _isCrawling = MutableStateFlow(false)
    val isCrawling: StateFlow<Boolean> = _isCrawling.asStateFlow()

    init {
        loadCachedJobsOnly()
    }

    fun loadCachedJobsOnly() {
        viewModelScope.launch {
            val cachedJobs = repository.loadCache()
            if (cachedJobs.isNotEmpty()) {
                _uiState.value = HomeUiState.Success(cachedJobs)
            } else {
                _uiState.value = HomeUiState.Success(emptyList())
            }
        }
    }

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun searchJobs() {
        viewModelScope.launch {
            _isCrawling.value = true
            // 1. Load cached jobs first (if any) to display immediately
            val cachedJobs = repository.loadCache()
            if (cachedJobs.isNotEmpty()) {
                _uiState.value = HomeUiState.Success(cachedJobs)
            } else {
                _uiState.value = HomeUiState.Loading
            }

            // 2. Perform live network crawl in background
            try {
                val jobs = repository.getJobs(_searchQuery.value, maxPages = 10)
                _uiState.value = HomeUiState.Success(jobs)
            } catch (e: Exception) {
                // If offline and we already show cached data, keep showing it.
                // Otherwise, show the error view.
                if (cachedJobs.isEmpty()) {
                    _uiState.value = HomeUiState.Error(e.localizedMessage ?: "알 수 없는 오류가 발생했습니다.")
                }
            } finally {
                _isCrawling.value = false
            }
        }
    }

    // Record job statistics in the background when clicked from HomeScreen
    fun recordJobClickInBackground(jobItem: JobItem) {
        viewModelScope.launch {
            try {
                val details = repository.getJobDetails(jobItem.recIdx)
                if (details.mainWork != "정보 없음" && details.mainWork != "상세 이미지 참고") {
                    repository.recordJobView(jobItem, details)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
