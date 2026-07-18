package com.peanutbutter1001.saramcrawler.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.peanutbutter1001.saramcrawler.data.model.JobItem
import com.peanutbutter1001.saramcrawler.ui.theme.SaramcrawlerTheme
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel

// Import statements will be kept, just updating the file contents to only include HomeScreen and its Preview
import com.peanutbutter1001.saramcrawler.ui.components.BadgeTag
import com.peanutbutter1001.saramcrawler.ui.components.EmptyView
import com.peanutbutter1001.saramcrawler.ui.components.ErrorView
import com.peanutbutter1001.saramcrawler.ui.components.JobCard
import com.peanutbutter1001.saramcrawler.utils.IntentUtils
import com.peanutbutter1001.saramcrawler.ui.theme.NeonBackground
import com.peanutbutter1001.saramcrawler.ui.theme.NeonCardBg
import com.peanutbutter1001.saramcrawler.ui.theme.NeonCyan
import com.peanutbutter1001.saramcrawler.ui.theme.NeonOrange
import com.peanutbutter1001.saramcrawler.ui.theme.NeonPink
import com.peanutbutter1001.saramcrawler.ui.theme.NeonPurple

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onStatsClick: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val isCrawling by viewModel.isCrawling.collectAsState()
    val keyboardController = LocalSoftwareKeyboardController.current
    val context = LocalContext.current

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(NeonBackground, Color(0xFF070510))
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp)
        ) {
            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Saramin AI Finder",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    letterSpacing = 1.sp
                )
                
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val countText = when (val state = uiState) {
                        is HomeUiState.Success -> "${state.jobs.size}개 조회됨"
                        is HomeUiState.Loading -> "조회 중..."
                        is HomeUiState.Error -> "오류"
                    }
                    
                    Text(
                        text = countText,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        color = NeonCyan
                    )
                    
                    IconButton(
                        onClick = onStatsClick,
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Info,
                            contentDescription = "분석 통계",
                            tint = NeonCyan,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(4.dp))

            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Seoul Badge
                BadgeTag(text = "서울 전체", containerColor = NeonPurple.copy(alpha = 0.2f), textColor = NeonPurple)
                // Career Badge
                BadgeTag(text = "신입~3년이하", containerColor = NeonPink.copy(alpha = 0.2f), textColor = NeonPink)

                BadgeTag(text = "4년제대졸/무관", containerColor = NeonOrange.copy(alpha = 0.2f), textColor = NeonOrange)
            }

            Spacer(modifier = Modifier.height(4.dp))
            // Search Bar & Search Button Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { viewModel.updateSearchQuery(it) },
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .border(
                            width = 1.5.dp,
                            brush = Brush.horizontalGradient(listOf(NeonPurple, NeonCyan)),
                            shape = RoundedCornerShape(12.dp)
                        ),
                    placeholder = { Text("검색 키워드를 입력하세요 (예: AI)", color = Color.Gray, fontSize = 14.sp) },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = "검색 아이콘", tint = NeonCyan) },
                    singleLine = true,
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = NeonCardBg,
                        unfocusedContainerColor = NeonCardBg,
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        cursorColor = NeonCyan,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent
                    ),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(onSearch = {
                        keyboardController?.hide()
                        viewModel.searchJobs()
                    })
                )

                Button(
                    onClick = {
                        keyboardController?.hide()
                        viewModel.searchJobs()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = NeonPurple),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.height(56.dp)
                ) {
                    Text("검색", color = Color.White, fontWeight = FontWeight.Bold)
                }
            }

            // Linear Progress Indicator representing crawling status
            if (isCrawling) {
                Spacer(modifier = Modifier.height(4.dp))
                LinearProgressIndicator(
                    color = NeonCyan,
                    trackColor = NeonCardBg,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .clip(RoundedCornerShape(1.5.dp))
                )
                Spacer(modifier = Modifier.height(4.dp))
            } else {
                Spacer(modifier = Modifier.height(8.dp))
            }

            // Screen Content based on UI State
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1.5f),
                contentAlignment = Alignment.Center
            ) {
                when (val state = uiState) {
                    is HomeUiState.Loading -> {
                        CircularProgressIndicator(
                            color = NeonCyan,
                            strokeWidth = 4.dp,
                            modifier = Modifier.size(50.dp)
                        )
                    }
                    is HomeUiState.Error -> {
                        ErrorView(
                            message = state.message,
                            onRetry = { viewModel.searchJobs() }
                        )
                    }
                    is HomeUiState.Success -> {
                        val jobs = state.jobs
                        if (jobs.isEmpty()) {
                            EmptyView(keyword = searchQuery)
                        } else {
                            LazyColumn(
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                                contentPadding = PaddingValues(bottom = 24.dp),
                                modifier = Modifier.fillMaxSize()
                            ) {
                                items(jobs) { job ->
                                    JobCard(
                                        job = job,
                                        onClick = {
                                            // 1. Record stats in background
                                            viewModel.recordJobClickInBackground(job)
                                            // 2. Direct deep link open
                                            IntentUtils.openJobUrl(context, job.link)
                                        }
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun HomeScreenPreview() {
    SaramcrawlerTheme {
        HomeScreen(onStatsClick = {})
    }
}
