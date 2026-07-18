package com.peanutbutter1001.saramin_ai_finder.ui.screens

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.peanutbutter1001.saramin_ai_finder.data.model.StatsData
import com.peanutbutter1001.saramin_ai_finder.data.repository.SaraminRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class StatsViewModel @Inject constructor(
    private val repository: SaraminRepository
) : ViewModel() {

    private val _stats = MutableStateFlow(StatsData())
    val stats: StateFlow<StatsData> = _stats.asStateFlow()

    init {
        loadStats()
    }

    fun loadStats() {
        viewModelScope.launch {
            _stats.value = repository.loadStats()
        }
    }

    fun clearStats() {
        viewModelScope.launch {
            repository.clearStats()
            _stats.value = StatsData()
        }
    }
}
