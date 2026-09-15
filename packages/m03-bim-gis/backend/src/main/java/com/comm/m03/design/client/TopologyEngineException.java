package com.comm.m03.design.client;

/**
 * 拓扑引擎明确报错异常。
 *
 * <p>用于区分两类失败：</p>
 * <ul>
 *   <li>引擎返回 4xx/5xx —— 请求体或引擎逻辑本身有问题，属于"明确报错"，<b>禁止静默回退</b>
 *       （继续回退等于用本地伪造成果掩盖真实 bug），抛本异常向上暴露。</li>
 *   <li>引擎不可达/超时/反序列化失败 —— 引擎暂时性故障，允许回退本地算法（由调用方标记"降级"）。</li>
 * </ul>
 */
public class TopologyEngineException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    /**
     * @param message 错误描述（含 HTTP 状态码与响应体）
     */
    public TopologyEngineException(String message) {
        super(message);
    }

    /**
     * @param message 错误描述
     * @param cause   原始异常
     */
    public TopologyEngineException(String message, Throwable cause) {
        super(message, cause);
    }
}
