using TwinCsharp.Models;

namespace TwinCsharp.Services;

public interface ITwinDataService
{
    List<Device> GetDevices();
    Device? GetDevice(string code);
    List<Alert> GetAlerts();
    DashboardDto GetDashboard();
}
