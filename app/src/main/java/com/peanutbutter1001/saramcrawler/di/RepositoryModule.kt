package com.peanutbutter1001.saramcrawler.di

import android.content.Context
import com.peanutbutter1001.saramcrawler.data.repository.SaraminRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object RepositoryModule {

    @Provides
    @Singleton
    fun provideSaraminRepository(
        @ApplicationContext context: Context
    ): SaraminRepository {
        return SaraminRepository(context)
    }
}
