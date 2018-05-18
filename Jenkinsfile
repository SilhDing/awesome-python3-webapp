pipeline {
  agent any
  stages {
    stage('INIT') {
      steps {
        sh 'echo "run the app now!"'
      }
    }
    stage('RUN') {
      steps {
        sh 'python www/app.py'
      }
    }
  }
}