package com.peanutbutter1001.saramin_ai_finder.ui.screens

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel

// Color palette
private val NeonBackground = Color(0xFF0F0C20)
private val NeonCardBg = Color(0xFF1B1735)
private val NeonPurple = Color(0xFF8B5CF6)
private val NeonCyan = Color(0xFF06B6D4)
private val NeonPink = Color(0xFFEC4899)
private val NeonOrange = Color(0xFFF97316)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatsScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: StatsViewModel = hiltViewModel()
) {
    val stats by viewModel.stats.collectAsState()
    
    // Reload stats when entering
    LaunchedEffect(Unit) {
        viewModel.loadStats()
    }

    // Sort keywords by frequency (descending)
    val sortedKeywords = remember(stats.keywordCounts) {
        stats.keywordCounts.entries
            .filter { it.value > 0 }
            .sortedByDescending { it.value }
    }
    
    val maxCount = remember(sortedKeywords) {
        sortedKeywords.maxOfOrNull { it.value } ?: 1
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "관심 스택 통계",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "뒤로가기",
                            tint = Color.White
                        )
                    }
                },
                actions = {
                    if (sortedKeywords.isNotEmpty() || stats.viewedRecIdxs.isNotEmpty()) {
                        TextButton(onClick = { viewModel.clearStats() }) {
                            Text(
                                text = "초기화",
                                color = NeonPink,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NeonBackground
                )
            )
        },
        containerColor = NeonBackground,
        modifier = modifier.fillMaxSize()
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(NeonBackground, Color(0xFF070510))
                    )
                )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Overview Summary Card
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .border(
                            width = 1.dp,
                            color = NeonPurple.copy(alpha = 0.3f),
                            shape = RoundedCornerShape(16.dp)
                        ),
                    colors = CardDefaults.cardColors(containerColor = NeonCardBg)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "조회한 공고 분석 요약",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color.LightGray
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "${stats.viewedRecIdxs.size}개 공고",
                            fontSize = 32.sp,
                            fontWeight = FontWeight.Black,
                            color = NeonCyan
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "상세히 읽어본 AI/개발 채용 정보 수",
                            fontSize = 12.sp,
                            color = Color.Gray
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                // Chart Section
                Text(
                    text = "요구 기술 스택 TOP 8",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Start
                )

                Spacer(modifier = Modifier.height(12.dp))

                if (sortedKeywords.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "아직 수집된 스택 통계가 없습니다.\n관심 있는 채용 공고를 상세히 터치해 보세요!",
                            color = Color.Gray,
                            fontSize = 14.sp,
                            textAlign = TextAlign.Center,
                            lineHeight = 20.sp
                        )
                    }
                } else {
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(16.dp))
                            .border(
                                width = 1.dp,
                                color = Color.White.copy(alpha = 0.05f),
                                shape = RoundedCornerShape(16.dp)
                            ),
                        colors = CardDefaults.cardColors(containerColor = NeonCardBg)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(14.dp)
                        ) {
                            // Render top 8 keywords
                            sortedKeywords.take(8).forEachIndexed { index, entry ->
                                KeyWordRow(
                                    rank = index + 1,
                                    keyword = entry.key,
                                    count = entry.value,
                                    maxCount = maxCount
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun KeyWordRow(
    rank: Int,
    keyword: String,
    count: Int,
    maxCount: Int
) {
    val progress = count.toFloat() / maxCount.toFloat()
    
    // Animation for progress bar length expansion
    var targetProgress by remember { mutableStateOf(0f) }
    LaunchedEffect(progress) {
        targetProgress = progress
    }
    
    val animatedProgress by animateFloatAsState(
        targetValue = targetProgress,
        animationSpec = tween(durationMillis = 800)
    )

    Column(
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "$rank",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (rank <= 3) NeonCyan else Color.Gray,
                    modifier = Modifier.width(20.dp)
                )
                Text(
                    text = keyword,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White
                )
            }
            Text(
                text = "${count}회",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan
            )
        }
        
        Spacer(modifier = Modifier.height(6.dp))
        
        // Progress Bar
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(10.dp)
                .clip(RoundedCornerShape(5.dp))
                .background(Color.White.copy(alpha = 0.05f))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(animatedProgress)
                    .clip(RoundedCornerShape(5.dp))
                    .background(
                        brush = Brush.horizontalGradient(
                            colors = listOf(NeonPurple, NeonCyan)
                        )
                    )
            )
        }
    }
}
