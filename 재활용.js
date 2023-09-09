// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: blue; icon-glyph: trash-alt;
// 위젯 크기 설정
let widget = new ListWidget()
widget.setPadding(12, 12, 12, 12)

// 현재 시각 가져오기
let now = new Date()
let dayOfWeek = now.getDay() // 일요일(0)부터 토요일(6)까지의 값을 반환
let hour = now.getHours()
let yoil = ""
if (dayOfWeek === 0 && hour < 15) {yoil = "일요일 15시 이전"}
if (dayOfWeek === 0 && hour >= 15) {yoil = "일요일 15시 이후"}
if (dayOfWeek === 1) {yoil = "월요일"}
if (dayOfWeek === 2 && hour < 9) {yoil = "화요일 9시 이전"}
if (dayOfWeek === 2 && hour >= 9) {yoil = "화요일 9시 이후"}
if (dayOfWeek === 3 && hour < 15) {yoil = "수요일 15시 이전"}
if (dayOfWeek === 3 && hour >= 15) {yoil = "수요일 15시 이후"}
if (dayOfWeek === 4) {yoil = "목요일"}
if (dayOfWeek === 5 && hour < 9) {yoil = "금요일 9시 이전"}
if (dayOfWeek === 5 && hour >= 9) {yoil = "금요일 9시 이후"}
if (dayOfWeek === 6) {yoil = "토요일"}
let text = widget.addText(yoil)
widget.addText("")
// 텍스트 출력 조건 확인
if ((dayOfWeek === 0 && hour >= 15) ||  (dayOfWeek === 1) || (dayOfWeek === 2 && hour < 9) || (dayOfWeek === 3) || (dayOfWeek === 4) || (dayOfWeek === 5 && hour < 9)) {
  let text = widget.addText("종이, 재활용품 배출 가능")
  text.font = Font.boldSystemFont(20)
  text.textColor = Color.white()
}
else if ((dayOfWeek === 2 && hour > 9) || (dayOfWeek === 3 && hour <= 15)) {
  let text = widget.addText("재활용품 배출 가능")
  text.font = Font.boldSystemFont(20)
  text.textColor = Color.white()
}
else {
  let text = widget.addText("종이, 재활용품 배출 불가능")
  text.font = Font.boldSystemFont(20)
  text.textColor = Color.white()
}

// 배경 설정
widget.backgroundColor = new Color("#00b5e2")

if (config.runsInWidget) {
  // 위젯을 위한 설정
  Script.setWidget(widget)
  Script.complete()
} else {
  // 앱 실행을 위한 미리보기
  widget.presentSmall()
}

