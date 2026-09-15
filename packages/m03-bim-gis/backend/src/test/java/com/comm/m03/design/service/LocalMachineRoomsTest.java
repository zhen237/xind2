package com.comm.m03.design.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 纯单元测试：从任务本地 GeoJSON 顶层 {@code properties} 提取机房（{@code machine_rooms}）
 * 与路由类型（{@code route_type}）。无需 Spring 容器、无需数据库。
 *
 * <p>背景（真实事故，2026-09-15）：S1(m03) 任务加载 QGIS 导出的「摩洛哥基站设计样例」后，
 * 后端 {@code result_json} 只携带 6 个站点、丢失了顶层 {@code properties.machine_rooms}（6 个机房），
 * 前端遂退化成用站点几何中心造出 1 个虚拟「机房（汇聚点）」。本测试锁定：
 * <ul>
 *   <li>顶层 properties 解析出 machine_rooms（长度 6）；</li>
 *   <li>{@code extractMachineRooms} 补齐 camelCase 别名（roomId/roomType/routeType）后返回 6 个机房；</li>
 *   <li>机房纬度比对应基站偏南（约 0.0004°，即「在基站底下」），锁死语义；</li>
 *   <li>顶层 route_type 回填到每个机房；</li>
 *   <li>非法/空输入返回空集合且不抛异常。</li>
 * </ul>
 */
class LocalMachineRoomsTest {

    /** 被测类使用 Spring 注入的实例字段 objectMapper（故 parse/extract 为实例方法），此处用反射注入一个真实 mapper。 */
    private static DesignService newService() {
        DesignService service = new DesignService();
        try {
            Field field = DesignService.class.getDeclaredField("objectMapper");
            field.setAccessible(true);
            field.set(service, new ObjectMapper());
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("无法向 DesignService 注入 objectMapper", e);
        }
        return service;
    }

    /**
     * 摩洛哥样例：6 个 Point 站点（features）+ 顶层 properties 内 6 个 machine_rooms。
     * 机房经度与对应基站完全相同、纬度仅偏南 0.0004°（约 44m，即「在基站底下」）。
     */
    private static String buildMoroccoLocalGeoJson() {
        String[] siteIds = {"BTS-URBA-006", "BTS-URBA-007", "BTS-URBA-010",
                "BTS-URBA-011", "BTS-URBA-014", "BTS-URBA-015"};
        String[] names = {"URBAN-006", "URBAN-007", "URBAN-010", "URBAN-011", "URBAN-014", "URBAN-015"};
        double[] lons = {-8.5359125, -8.5265861, -8.5386048, -8.5292784, -8.5359125, -8.5265861};
        double[] lats = {33.2134738, 33.2134738, 33.2202306, 33.2202306, 33.2269873, 33.2269873};
        // 机房纬度 = 对应基站纬度 - 0.0004（在基站正下方偏南）
        double[] roomLats = {33.2130738, 33.2130738, 33.2198306, 33.2198306, 33.2265873, 33.2265873};

        StringBuilder sb = new StringBuilder();
        sb.append("{\"type\":\"FeatureCollection\",\"features\":[");
        for (int i = 0; i < siteIds.length; i++) {
            if (i > 0) {
                sb.append(",");
            }
            sb.append("{\"type\":\"Feature\",\"geometry\":{\"type\":\"Point\",\"coordinates\":[")
                    .append(lons[i]).append(",").append(lats[i]).append("]},")
                    .append("\"properties\":{\"site_id\":\"").append(siteIds[i]).append("\",")
                    .append("\"name\":\"").append(names[i]).append("\",")
                    .append("\"served_room_id\":\"ROOM-").append(siteIds[i]).append("\"}}");
        }
        sb.append("],\"properties\":{\"band\":\"3.5GHz\",\"tower_height\":35,\"route_type\":\"optimal\",")
                .append("\"machine_rooms\":[");
        for (int i = 0; i < siteIds.length; i++) {
            if (i > 0) {
                sb.append(",");
            }
            sb.append("{\"room_id\":\"ROOM-").append(siteIds[i]).append("\",")
                    .append("\"name\":\"").append(names[i]).append("机房\",")
                    .append("\"room_type\":\"汇聚机房\",")
                    .append("\"longitude\":").append(lons[i]).append(",")
                    .append("\"latitude\":").append(roomLats[i]).append(",")
                    .append("\"capacity\":10,\"deviceType\":\"communication_room\",\"fibreUsed\":6.0}");
        }
        sb.append("],\"saved_at\":\"2026-09-13T00:00:00\"}}");
        return sb.toString();
    }

    @Test
    @DisplayName("顶层 properties 解析出 6 个机房（machine_rooms 为长度 6 的 List）")
    void parsesTopLevelPropertiesWithSixMachineRooms() {
        DesignService service = newService();

        Map<String, Object> meta = service.parseLocalGeoJsonProperties(buildMoroccoLocalGeoJson());

        Object raw = meta.get("machine_rooms");
        assertTrue(raw instanceof List, "machine_rooms 应为 List，实际=" + (raw == null ? "null" : raw.getClass()));
        assertEquals(6, ((List<?>) raw).size(), "必须恰好 6 个机房（而非退化后的 1 个汇聚点）");
        assertEquals("optimal", meta.get("route_type"), "顶层 route_type 应为 optimal");
    }

    @Test
    @DisplayName("extractMachineRooms 返回 6 个机房，且 roomId/room_id 双写、routeType 由顶层回填")
    void extractsSixRoomsWithAliasesAndRouteType() {
        DesignService service = newService();
        Map<String, Object> meta = service.parseLocalGeoJsonProperties(buildMoroccoLocalGeoJson());

        List<Map<String, Object>> rooms = service.extractMachineRooms(meta);

        assertEquals(6, rooms.size(), "应提取出 6 个机房");

        Map<String, Object> first = rooms.get(0);
        // camelCase 别名生效，且原始 snake_case key 保留
        assertEquals("ROOM-BTS-URBA-006", first.get("roomId"), "roomId 别名应等于 room_id");
        assertEquals("ROOM-BTS-URBA-006", first.get("room_id"), "原始 room_id 应保留");
        assertEquals(first.get("room_id"), first.get("roomId"), "roomId 与 room_id 必须一致");

        // 坐标：机房经度与基站相同，纬度偏南 0.0004°（在基站底下）
        double lon = ((Number) first.get("longitude")).doubleValue();
        double lat = ((Number) first.get("latitude")).doubleValue();
        assertEquals(-8.5359125, lon, 1e-6, "机房经度应与基站一致");
        assertEquals(33.2130738, lat, 1e-6, "机房纬度应约为基站纬度偏南 0.0004");
        assertNotEquals(33.2134738, lat, 1e-6, "机房纬度必须不等于基站纬度（机房在基站底下偏南）");

        // 顶层 route_type=optimal 回填到每个机房
        for (Map<String, Object> room : rooms) {
            assertEquals("optimal", room.get("routeType"),
                    "roomType 别名/routeType 回填失败: " + room.get("room_id"));
            assertEquals("汇聚机房", room.get("roomType"), "room_type → roomType 别名应生效");
        }
    }

    @Test
    @DisplayName("每个机房 longitude/latitude 均非空且经度为负（摩洛哥）")
    void everyRoomHasCoordinatesInMorocco() {
        DesignService service = newService();
        List<Map<String, Object>> rooms =
                service.extractMachineRooms(service.parseLocalGeoJsonProperties(buildMoroccoLocalGeoJson()));

        for (Map<String, Object> room : rooms) {
            Object lon = room.get("longitude");
            Object lat = room.get("latitude");
            assertNotNull(lon, "机房经度不得为空: " + room.get("room_id"));
            assertNotNull(lat, "机房纬度不得为空: " + room.get("room_id"));
            assertTrue(((Number) lon).doubleValue() < 0,
                    "机房经度必须为负（摩洛哥），实际=" + lon + ", roomId=" + room.get("room_id"));
        }
    }

    @Test
    @DisplayName("边界：null / 非 JSON 输入返回空 map（不抛异常）；空 map 提取机房返回空 List")
    void returnsEmptyOnInvalidInput() {
        DesignService service = newService();

        assertTrue(service.parseLocalGeoJsonProperties(null).isEmpty(), "null 输入应返回空 map");
        assertTrue(service.parseLocalGeoJsonProperties("   ").isEmpty(), "空白输入应返回空 map");
        assertTrue(service.parseLocalGeoJsonProperties("not json").isEmpty(), "非 JSON 输入应返回空 map 且不抛异常");

        assertTrue(service.extractMachineRooms(Collections.emptyMap()).isEmpty(), "空 map 应返回空 List");
        assertTrue(service.extractMachineRooms(null).isEmpty(), "null 应返回空 List");
    }
}
