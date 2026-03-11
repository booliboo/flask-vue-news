import axios from 'axios'

const service = axios.create({
    baseURL: 'http://localhost:5000/api',
    timeout: 5000
})

// 请求拦截器：自动注入 JWT Token
service.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
})

export default service