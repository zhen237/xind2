namespace TwinCsharp.Models;

/// <summary>
/// 告警实体。字段命名/类型对齐 packages/m05-twin-ops/backend 的 Alert.java。
/// </summary>
public class Alert
{
    public long Id { get; set; }
    public long? DeviceId { get; set; }
    public string? DeviceCode { get; set; }
    public string? AlertContent { get; set; }
    /// <summary>1=提示 2=警告 3=严重</summary>
    public int? Level { get; set; }
    /// <summary>0=未处理 1=已处理</summary>
    public int? Status { get; set; }
    public string? Source { get; set; }
    public string? OrderNo { get; set; }
    public DateTime? CreateTime { get; set; }
    public DateTime? UpdateTime { get; set; }
}
