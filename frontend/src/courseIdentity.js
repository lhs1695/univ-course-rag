const identities = [
  { match: /心理/, symbol: '心', tint: '#fde0ec', description: '从现象出发，理解行为与心智。' },
  { match: /代数|数学/, symbol: '∑', tint: '#dcecfa', description: '理清定义，让推导有迹可循。' },
  { match: /历史/, symbol: '史', tint: '#ffe8d4', description: '回到史料，连接事件与时代。' },
  { match: /哲学/, symbol: '思', tint: '#d9f3e1', description: '追问概念，梳理论证的来路。' },
];
export function courseIdentity(title = '') {
  return identities.find(item => item.match.test(title)) || { symbol: '册', tint: '#e6e0f5', description: '带着问题阅读，带着依据理解。' };
}
