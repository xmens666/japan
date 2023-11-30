// 获取乘客数量元素
var passengerCountElement = document.querySelector('.--mr-8'); 
var passengerCount = passengerCountElement ? parseInt(passengerCountElement.textContent.trim()) : 0;

// 获取所有匹配的司机说明元素
var driverInstructionElements = document.querySelectorAll('div.--break-words.--flex-1');
var driverInstructions = Array.from(driverInstructionElements).map(element => element.textContent.trim());

// 定义关键词
var childKeywords = ["婴儿", "安全", "儿童", "宝宝", "baby", "child", "children", "座椅"];

// 检查是否包含关键词
var containsChildKeyword = driverInstructions.some(instruction => 
    childKeywords.some(keyword => instruction.includes(keyword))
);

// 判断是否符合条件
var isQualified = passengerCount <= 4 && !containsChildKeyword;

// 打印相关信息以便调试
console.log("乘客数量: " + passengerCount);
console.log("司机说明: " + driverInstructions.join('; ')); // 将所有司机说明连接成一个字符串
console.log("是否提及婴儿座椅: " + containsChildKeyword);
console.log("是否合格: " + isQualified);

// 准备返回的数据
var result = {
    "passengerCount": passengerCount,
    "driverInstructions": driverInstructions, // 用数组保存所有司机说明
    "containsChildKeyword": containsChildKeyword,
    "isQualified": isQualified
};

console.log(result); // 打印结果到控制台

return result; // 返回结果
