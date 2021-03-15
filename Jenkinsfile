#!/usr/bin/env groovy
node('commonagent') {
  stage('git checkout') {
    step([$class: 'WsCleanup'])
    checkout(scm)
  }
  stage('Prepare python environment') {
    sh('make ci_docker_build')
  }
  stage('setup') {
    sh('make ci_setup')
  }
  stage('test') {
    sh('make ci_test')
  }
  stage('security') {
    sh('make ci_security_checks')
  }
  stage('package') {
    sh('make ci_package')
  }
  stage('publish') {
    sh("""
        make publish BUCKET_NAME=txm-lambda-functions-tools
        make publish BUCKET_NAME=txm-lambda-functions-integration
        make publish BUCKET_NAME=txm-lambda-functions-production
    """)
  }
}
