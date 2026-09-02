namespace TwinCsharp.Models;

/// <summary>
/// 施工监测看板聚合数据。
/// </summary>
public class DashboardDto
{
    public int TotalDevices { get; set; }
    public int OnlineCount { get; set; }
    public int OfflineCount { get; set; }
    public int FaultCount { get; set; }
    public int AlertTotal { get; set; }
    public int AlertActive { get; set; }
    public Dictionary<string, int> AlertByLevel { get; set; } = new();
    public Dictionary<string, int> DeviceTypeDistribution { get; set; } = new();
    public List<Alert> RecentAlerts { get; set; } = new();
}
