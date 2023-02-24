resource "aws_cloudwatch_event_rule" "login-notification" {
  name        = "Login-Detect"
  description = "Trigger Notification when Login is Detected"
  event_pattern = jsonencode(
    {
      "detail-type" : [
        "AWS Console Sign In via CloudTrail"
      ],
      "detail" : {
        "eventSource" : [
          "signin.amazonaws.com"
        ],
        "eventName" : [
          "ConsoleLogin"
        ]
      }
  })
}
