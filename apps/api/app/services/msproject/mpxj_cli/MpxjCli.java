/*
 * US-069 — Wrapper Java para MPXJ.
 *
 * MPXJ (net.sf.mpxj) no distribuye una CLI lista para usar que exporte
 * al shape de ParsedTask del backend. Este wrapper carga el archivo
 * binario de MS Project (.mpp, .mpx, .mpt, etc.) con UniversalProjectReader
 * y emite un JSON mínimo por stdout con la misma forma que produce el
 * parser XLSX (apps/api/app/services/xlsx_task_parser.py).
 *
 * Uso:
 *   java -cp "/opt/mpxj/lib/*:/opt/mpxj/cli" MpxjCli <input.mpp>
 *
 * Salida (stdout, UTF-8):
 *   {
 *     "tasks": [
 *       {
 *         "row_number": 2,
 *         "name": "Analisis",
 *         "wbs": "1",
 *         "start_date": "2026-01-01",
 *         "end_date": "2026-01-10",
 *         "duration_days": 10,
 *         "progress": 50,
 *         "is_milestone": false,
 *         "predecessors_raw": "1FS",
 *         "resources_raw": "Juan, Maria"
 *       }
 *     ]
 *   }
 *
 * Errores: exit code 2 con mensaje en stderr. No emite stack traces para
 * no filtrar detalles del host al cliente.
 */
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.StringJoiner;

import net.sf.mpxj.ProjectFile;
import net.sf.mpxj.Relation;
import net.sf.mpxj.Resource;
import net.sf.mpxj.ResourceAssignment;
import net.sf.mpxj.Task;
import net.sf.mpxj.reader.UniversalProjectReader;

public final class MpxjCli {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("usage: MpxjCli <input-file>");
            System.exit(2);
        }

        File input = new File(args[0]);
        if (!input.canRead()) {
            System.err.println("cannot read input file");
            System.exit(2);
        }

        ProjectFile project;
        try {
            project = new UniversalProjectReader().read(input);
        } catch (Exception e) {
            // Mensaje genérico — el endpoint traduce a 422 con "archivo
            // corrupto o versión no soportada".
            System.err.println("MPXJ could not read file: " + safeMessage(e));
            System.exit(2);
            return;
        }

        if (project == null) {
            System.err.println("MPXJ returned a null project");
            System.exit(2);
            return;
        }

        List<Task> tasks = project.getTasks();
        StringBuilder out = new StringBuilder(4096);
        out.append("{\"tasks\":[");

        boolean first = true;
        int rowNumber = 1;
        for (Task task : tasks) {
            if (task == null) continue;
            String name = task.getName();
            if (name == null || name.isEmpty()) continue;
            // Saltamos el "Root" / project summary task (UID 0 sin WBS) para
            // alinear con el comportamiento del parser XML (xml_parser.py).
            Integer uid = task.getUniqueID();
            if (uid != null && uid == 0 && task.getWBS() == null) continue;

            rowNumber++;
            if (!first) out.append(',');
            first = false;

            out.append('{');
            appendInt(out, "row_number", rowNumber);
            appendStr(out, "name", name);
            appendNullableStr(out, "wbs", task.getWBS());
            appendNullableDate(out, "start_date", task.getStart());
            appendNullableDate(out, "end_date", task.getFinish());
            appendNullableInt(
                out,
                "duration_days",
                task.getDuration() != null
                    ? (int) Math.round(task.getDuration().convertUnits(
                        net.sf.mpxj.TimeUnit.DAYS, project.getProjectProperties()
                      ).getDuration())
                    : null
            );
            appendInt(
                out,
                "progress",
                task.getPercentComplete() != null
                    ? task.getPercentComplete().intValue() : 0
            );
            appendBool(out, "is_milestone", Boolean.TRUE.equals(task.getMilestone()));
            appendNullableStr(out, "predecessors_raw", formatPredecessors(task));
            appendNullableStr(out, "resources_raw", formatResources(task), /*last=*/true);
            out.append('}');
        }

        out.append("]}");
        // Escribir UTF-8 explícito para que el subprocess Python reciba
        // caracteres correctos sin depender del default charset del JVM.
        System.out.write(out.toString().getBytes(StandardCharsets.UTF_8), 0, out.length());
        System.out.flush();
    }

    private static String formatPredecessors(Task task) {
        // Formato estilo MS Project: "1,2,3" (solo UIDs, tipo FS implícito)
        // — suficiente para el wizard de mapeo (US-070) que tratará la
        // cadena como display-only. Tipo/lag detallados se recuperan en
        // v2 vía un parser nativo, no desde esta CLI.
        List<Relation> preds = task.getPredecessors();
        if (preds == null || preds.isEmpty()) return null;
        StringJoiner j = new StringJoiner(",");
        for (Relation r : preds) {
            if (r == null || r.getTargetTask() == null) continue;
            Integer uid = r.getTargetTask().getUniqueID();
            if (uid == null) continue;
            j.add(uid.toString());
        }
        String s = j.toString();
        return s.isEmpty() ? null : s;
    }

    private static String formatResources(Task task) {
        List<ResourceAssignment> ra = task.getResourceAssignments();
        if (ra == null || ra.isEmpty()) return null;
        StringJoiner j = new StringJoiner(", ");
        for (ResourceAssignment a : ra) {
            if (a == null) continue;
            Resource res = a.getResource();
            if (res == null) continue;
            String name = res.getName();
            if (name != null && !name.isEmpty()) j.add(name);
        }
        String s = j.toString();
        return s.isEmpty() ? null : s;
    }

    // --- helpers de serialización JSON mínimos (sin dependencias) ---

    private static void appendStr(StringBuilder out, String key, String v) {
        out.append('"').append(key).append("\":");
        out.append(jsonString(v)).append(',');
    }

    private static void appendNullableStr(StringBuilder out, String key, String v) {
        appendNullableStr(out, key, v, false);
    }

    private static void appendNullableStr(StringBuilder out, String key, String v, boolean last) {
        out.append('"').append(key).append("\":");
        if (v == null || v.isEmpty()) out.append("null");
        else out.append(jsonString(v));
        if (!last) out.append(',');
    }

    private static void appendNullableDate(StringBuilder out, String key, java.time.LocalDateTime dt) {
        out.append('"').append(key).append("\":");
        if (dt == null) out.append("null");
        else out.append('"').append(dt.toLocalDate().toString()).append('"');
        out.append(',');
    }

    private static void appendInt(StringBuilder out, String key, int v) {
        out.append('"').append(key).append("\":").append(v).append(',');
    }

    private static void appendNullableInt(StringBuilder out, String key, Integer v) {
        out.append('"').append(key).append("\":");
        if (v == null) out.append("null");
        else out.append(v.intValue());
        out.append(',');
    }

    private static void appendBool(StringBuilder out, String key, boolean v) {
        out.append('"').append(key).append("\":").append(v ? "true" : "false").append(',');
    }

    private static String jsonString(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder(s.length() + 2);
        b.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                case '\b': b.append("\\b"); break;
                case '\f': b.append("\\f"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        b.append('"');
        return b.toString();
    }

    private static String safeMessage(Throwable t) {
        String m = t.getMessage();
        return m == null ? t.getClass().getSimpleName() : m;
    }

    private MpxjCli() {}
}
