package com.peanutbutter1001.saramin_ai_finder.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.navigation3.rememberViewModelStoreNavEntryDecorator
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.runtime.rememberSaveableStateHolderNavEntryDecorator
import androidx.navigation3.ui.NavDisplay
import com.peanutbutter1001.saramin_ai_finder.ui.screens.HomeScreen
import com.peanutbutter1001.saramin_ai_finder.ui.screens.StatsScreen

/**
 * 앱 전체 네비게이션 그래프 (Navigation 3).
 */
@Composable
fun AppNavHost(modifier: Modifier = Modifier) {
    val backStack = rememberNavBackStack(Home)

    NavDisplay(
        backStack = backStack,
        modifier = modifier,
        onBack = { backStack.removeLastOrNull() },
        entryDecorators = listOf(
            rememberSaveableStateHolderNavEntryDecorator(),
            rememberViewModelStoreNavEntryDecorator(),
        ),
        entryProvider = entryProvider {
            entry<Home> {
                HomeScreen(
                    onStatsClick = { backStack.add(Stats) }
                )
            }
            entry<Stats> {
                StatsScreen(
                    onBack = { backStack.removeLastOrNull() }
                )
            }
        },
    )
}
