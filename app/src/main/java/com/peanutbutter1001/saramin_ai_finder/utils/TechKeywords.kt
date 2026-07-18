package com.peanutbutter1001.saramin_ai_finder.utils

object TechKeywords {
    // Tech stack keyword patterns with English and Korean synonyms
    val KEYWORD_PATTERNS = mapOf(
        "n8n" to listOf(Regex("(?i)n8n")),
        "Harness" to listOf(Regex("(?i)하네스")),
        "PyTorch" to listOf(Regex("(?i)PyTorch"), Regex("(?i)파이토치")),
        "TensorFlow" to listOf(Regex("(?i)TensorFlow"), Regex("(?i)텐서플로"), Regex("(?i)텐서플로우")),
        "LLM" to listOf(Regex("(?i)\\bLLM\\b"), Regex("(?i)거대언어모델"), Regex("(?i)거대\\s*언어\\s*모델")),
        "RAG" to listOf(Regex("(?i)\\bRAG\\b"), Regex("(?i)검색증강생성"), Regex("(?i)검색\\s*증강\\s*생성")),
        "Deep Learning" to listOf(Regex("(?i)Deep\\s*Learning"), Regex("(?i)딥러닝"), Regex("(?i)딥\\s*러닝")),
        "Machine Learning" to listOf(Regex("(?i)Machine\\s*Learning"), Regex("(?i)머신러닝"), Regex("(?i)머신\\s*러닝")),
        "Computer Vision" to listOf(Regex("(?i)Computer\\s*Vision"), Regex("(?i)컴퓨터비전"), Regex("(?i)컴퓨터\\s*비전")),
        "NLP" to listOf(Regex("(?i)\\bNLP\\b"), Regex("(?i)자연어처리"), Regex("(?i)자연어\\s*처리")),
        "LangChain" to listOf(Regex("(?i)LangChain"), Regex("(?i)랭체인")),
        "LangGraph" to listOf(Regex("(?i)LangGraph"), Regex("(?i)랭그래프")),
        "Python" to listOf(Regex("(?i)Python"), Regex("(?i)파이썬")),
        "Java" to listOf(Regex("(?i)\\bJava\\b"), Regex("(?i)자바(?!스크립트)")),
        "Kotlin" to listOf(Regex("(?i)Kotlin"), Regex("(?i)코틀린")),
        "TypeScript" to listOf(Regex("(?i)TypeScript"), Regex("(?i)타입스크립트"), Regex("(?i)\\bTS\\b")),
        "JavaScript" to listOf(Regex("(?i)JavaScript"), Regex("(?i)자바스크립트"), Regex("(?i)\\bJS\\b")),
        "MySQL" to listOf(Regex("(?i)MySQL"), Regex("(?i)마이SQL")),
        "PostgreSQL" to listOf(Regex("(?i)PostgreSQL"), Regex("(?i)포스트그레")),
        "Redis" to listOf(Regex("(?i)Redis"), Regex("(?i)레디스")),
        "MongoDB" to listOf(Regex("(?i)MongoDB"), Regex("(?i)몽고디비")),
        "Elasticsearch" to listOf(Regex("(?i)Elasticsearch"), Regex("(?i)엘라스틱서치")),
        "SQL" to listOf(Regex("(?i)\\bSQL\\b"), Regex("(?i)에스큐엘")),
        "Spring Boot" to listOf(Regex("(?i)Spring\\s*Boot"), Regex("(?i)스프링\\s*부트"), Regex("(?i)스프링부트")),
        "Spring" to listOf(Regex("(?i)\\bSpring\\b"), Regex("(?i)스프링")),
        "Node.js" to listOf(Regex("(?i)Node\\.?js"), Regex("(?i)노드")),
        "Django" to listOf(Regex("(?i)Django"), Regex("(?i)장고")),
        "FastAPI" to listOf(Regex("(?i)FastAPI"), Regex("(?i)패스트API")),
        "React" to listOf(Regex("(?i)\\bReact\\b"), Regex("(?i)리액트")),
        "Next.js" to listOf(Regex("(?i)Next\\.?js"), Regex("(?i)넥스트js")),
        "AWS" to listOf(Regex("(?i)\\bAWS\\b"), Regex("(?i)아마존웹서비스")),
        "GCP" to listOf(Regex("(?i)\\bGCP\\b"), Regex("(?i)구글클라우드")),
        "Docker" to listOf(Regex("(?i)Docker"), Regex("(?i)도커")),
        "Kubernetes" to listOf(Regex("(?i)Kubernetes"), Regex("(?i)쿠버네티스"), Regex("(?i)k8s")),
        "Git" to listOf(Regex("(?i)\\bGit\\b"), Regex("(?i)깃")),
        "Linux" to listOf(Regex("(?i)Linux"), Regex("(?i)리눅스"))
    )
}
