namespace TwinCsharp.Models;

/// <summary>
/// 设备实体。字段命名/类型对齐 packages/m05-twin-ops/backend 的 Device.java。
/// </summary>
public class Device
{
    public long Id { get; set; }
    public string? DeviceCode { get; set; }
    public string? DeviceName { get; set; }
    public string? DeviceType { get; set; }
    public string? StationCode { get; set; }
    public DateTime? InstallTime { get; set; }
    /// <summary>0=离线 1=在线 2=故障</summary>
    public int? Status { get; set; }
    public string? Manufacturer { get; set; }
    public string? Model { get; set; }
    public DateTime? CreateTime { get; set; }

    /// <summary>孪生扩展状态（数字孪生实时指标），S5 设备孪生状态页使用</summary>
    public TwinState? Twin { get; set; }
}

/// <summary>
/// 孪生实时状态（非 m05 字段，属于 S5 孪生扩展）。
/// </summary>
public class TwinState
{
    public double? Temperature { get; set; }   // 当前温度 ℃
    public double? Load { get; set; }          // 负载 %
    public long? RuntimeMinutes { get; set; }  // 累计运行分钟
    public DateTime? LastSync { get; set; }    // 最后一次孪生同步时间
    public int? Health { get; set; }           // 健康度 0-100
}
