/*
 * Copyright (c) 2013, Institute for Pervasive Computing, ETH Zurich
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the Institute nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE INSTITUTE AND CONTRIBUTORS ``AS IS'' AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE INSTITUTE OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
 * OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 *
 * This file is part of the Contiki operating system.
 */

/**
 * \file
 *     CoAP client example.
 * \author
 *      Matthias Kovatsch <kovatsch@inf.ethz.ch>
 *      Dries Van Leemput <dries.vanleemput@ugent.be>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "contiki.h"
#include "contiki-net.h"
#include "coap-engine.h"
#include "coap-blocking-api.h"
#include "net/routing/routing.h"
#include "random.h"
#include "net/netstack.h"
#include "orchestra.h"
#include "rpl-private.h"
#include "link-stats.h"

#include "sys/node-id.h"
#include "sys/energest.h"

/* Log configuration */
#include "coap-log.h"
#define LOG_MODULE "App"
#define LOG_LEVEL  LOG_LEVEL_APP

#define SERVER_EP "coap://[fd00::201:1:1:1]"

#define SEND_INTERVAL		  3*60*60*CLOCK_SECOND
#define PRED_INTERVAL     (10 * CLOCK_SECOND)

/* UDP */
#include "net/ipv6/simple-udp.h"
#define UDP_PORT_RECEIVER 5678
#define UDP_PORT_SENDER 31001

static struct simple_udp_connection udp_conn;
void process_udpmessage(const char* message);

PROCESS(coap_client, "CoAP Client");
AUTOSTART_PROCESSES(&coap_client);

static unsigned long
to_mseconds(uint64_t time)
{
  return (unsigned long)(time*1000 / ENERGEST_SECOND);
}

static struct etimer et;
static struct etimer et2;

/* Example URIs that can be queried. */
#define NUMBER_OF_URLS 5
/* leading and ending slashes only for demo purposes, get cropped automatically when setting the Uri-Path */
char *service_urls[NUMBER_OF_URLS] =
{ ".well-known/core", "test/chunks"};

/* This function is will be passed to COAP_BLOCKING_REQUEST() to handle responses. */
void
client_chunk_handler(coap_message_t *response)
{
  const uint8_t *chunk;

  if(response == NULL) {
    puts("Request timed out");
    return;
  }

  int len = coap_get_payload(response, &chunk);

  LOG_INFO("|%.*s", len, (char *)chunk);
}

static void
udp_rx_callback(struct simple_udp_connection *c,
         const uip_ipaddr_t *sender_addr,
         uint16_t sender_port,
         const uip_ipaddr_t *receiver_addr,
         uint16_t receiver_port,
         const uint8_t *data,
         uint16_t datalen)
{
  int sf_divisor;
    if (sscanf((char *)data, "Increase SF %d", &sf_divisor) == 1) {
        LOG_INFO("Received message '%.*s' from ", datalen, (char *) data);
        LOG_INFO_6ADDR(sender_addr);
        LOG_INFO_("\n");
        orchestra_callback_change_sf(sf_divisor);
    } else {
        LOG_INFO("Failed to extract divisor from received data: %.*s\n", datalen, (char *) data);
    }
}

PROCESS_THREAD(coap_client, ev, data)
{
  static coap_endpoint_t server_ep;
  PROCESS_BEGIN();

  NETSTACK_MAC.on();

  static coap_message_t request[1];      /* This way the packet can be treated as pointer as usual. */

  coap_endpoint_parse(SERVER_EP, strlen(SERVER_EP), &server_ep);

  /* Spread out CoAP GET messages to prevent network flooding */
  if(node_id < 9){
    etimer_set(&et, ((node_id-1)*CLOCK_SECOND*(SEND_INTERVAL/9)) % (SEND_INTERVAL));
  } else {
    etimer_set(&et, ((node_id-2)*CLOCK_SECOND*(SEND_INTERVAL/9)) % (SEND_INTERVAL));
  }
  
  etimer_set(&et2, PRED_INTERVAL);
  simple_udp_register(&udp_conn, UDP_PORT_RECEIVER, NULL, UDP_PORT_SENDER, udp_rx_callback);

  while(1) {
    PROCESS_YIELD();

    if(etimer_expired(&et)) {
      LOG_INFO("--Toggle timer--\n");
      etimer_set(&et, SEND_INTERVAL);
      if(NETSTACK_ROUTING.node_is_reachable()) {
        /* prepare request, TID is set by COAP_BLOCKING_REQUEST() */
        coap_init_message(request, COAP_TYPE_CON, COAP_GET, 0);
        int resource = 1;
        coap_set_header_uri_path(request, service_urls[resource]);

        const char msg[] = "Toggle!";

        coap_set_payload(request, (uint8_t *)msg, sizeof(msg) - 1);

        LOG_INFO_COAP_EP(&server_ep);
        LOG_INFO_("\n");

        COAP_BLOCKING_REQUEST(&server_ep, request, client_chunk_handler);

        LOG_INFO("\n--Done--\n");
      } else {
        LOG_INFO("Not reachable yet\n");
      }      
    }
    if(etimer_expired(&et2)){
      rpl_instance_t *default_instance = rpl_get_default_instance();
      rpl_parent_t *pp = rpl_get_preferred_parent(default_instance);
      if(pp != NULL){
        // Get ETX
        const struct link_stats *stats = rpl_get_parent_link_stats(pp);
        uint16_t etxx = stats->etx;
        const linkaddr_t *pp_lladdr = rpl_get_parent_lladdr(pp);
        printf("Node ID: %u, PREDICT %lu ms, RX %lu ms, TX %lu ms, ETX %u, PP %u\n", node_id, clock_time(),to_mseconds(energest_type_time(ENERGEST_TYPE_LISTEN)),
            to_mseconds(energest_type_time(ENERGEST_TYPE_TRANSMIT)), etxx, pp_lladdr->u8[LINKADDR_SIZE-1]);
      } else{
        printf("Node ID: %u, PREDICT %lu ms, RX %lu ms, TX %lu ms\n", node_id, clock_time(),to_mseconds(energest_type_time(ENERGEST_TYPE_LISTEN)),
            to_mseconds(energest_type_time(ENERGEST_TYPE_TRANSMIT)));
      }
      
      etimer_reset(&et2);
    }
  }

  PROCESS_END();
}
